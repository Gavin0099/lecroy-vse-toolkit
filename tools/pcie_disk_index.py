"""Disk-backed, capture-ordered PCIe rows and nearest-preceding associations.

SQLite is a local spool/index, not a new protocol rule. No chunk closes a request.
All queries use the current sealed index; connections have an 8 MiB page cache.
"""
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sqlite3
import os

import pcie_large_io as large
import pcie_event_coverage as nav

FORMAT = 'pcie.disk-index/v1'
GRAPH_ROWS = 512


def connect(path, readonly=False):
    c = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True) if readonly else sqlite3.connect(path)
    c.execute('PRAGMA cache_size=-8192')
    c.execute('PRAGMA temp_store=FILE')
    if not readonly:
        c.execute('PRAGMA journal_mode=DELETE')
        c.execute('PRAGMA synchronous=FULL')
    return c


def chunks(value):
    # The common one-Completion request can use one bounded record encoding.
    # Large fanout still streams; no whole transaction collection is collected.
    if type(value) is dict and isinstance(value.get('completions'), CompletionRows):
        completions=value['completions']
        if len(completions)<=16:
            record=dict(value,completions=[c for c in completions] if len(completions) else [])
            yield json.dumps(record,ensure_ascii=False,separators=(',',':'),sort_keys=True)
            return
    # Native row/field/role records are flat, bounded dictionaries. Encode one
    # record with the C-backed JSON encoder rather than dozens of Python chunks.
    # Lazy nested completion sequences retain the streaming fallback below.
    if type(value) is dict and all(type(k) is str for k in value) and all(
            v is None or type(v) in (str,int,float,bool) or
            type(v) is list and len(v)<=16 and all(x is None or type(x) in (str,int,float,bool) for x in v)
            for v in value.values()):
        yield json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True)
    elif isinstance(value, Mapping):
        yield '{'
        for i, key in enumerate(sorted(value)):
            if i: yield ','
            yield json.dumps(key, ensure_ascii=False)+':'
            yield from chunks(value[key])
        yield '}'
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        yield '['
        for i, item in enumerate(value):
            if i: yield ','
            yield from chunks(item)
        yield ']'
    else:
        yield json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def write_array(path, rows, cancelled=lambda:False):
    """Canonical JSON array without materializing the array or nested completions."""
    path=Path(path);partial=path.with_name(path.name+'.partial');size=0;checked=0
    with partial.open('xb', buffering=256*1024) as f:
        f.write(b'[')
        for i, row in enumerate(rows):
            if i: f.write(b',')
            for text in chunks(row):
                data=text.encode('utf-8');size+=len(data)
                if size>large.DEFAULTS['dense_probe_bytes']:raise large.ResourceLimit('Indexed JSON export exceeds disk budget')
                if size-checked>=1024*1024:
                    if cancelled():raise InterruptedError('Cancelled during indexed evidence export')
                    large.check_disk(path.parent);checked=size
                f.write(data)
        f.write(b']\n');f.flush();os.fsync(f.fileno())
    if path.exists():raise FileExistsError(path)
    partial.rename(path)
    return nav.digest(path)


class PacketMap(Mapping):
    def __init__(self, fields, ordinal=False):self.fields,self.ordinal=fields,ordinal
    def __len__(self):return len(self.fields)
    def __iter__(self):
        for (index,) in self.fields.db.execute('SELECT packet FROM fields ORDER BY ordinal'):yield index
    def __getitem__(self,index):
        row=self.fields.db.execute('SELECT ordinal,data FROM fields WHERE packet=?',(index,)).fetchone()
        if row is None:raise KeyError(index)
        return row[0] if self.ordinal else json.loads(row[1])


class Fields(Sequence):
    def __init__(self, path):
        self.path=Path(path);self.db=connect(path,True)
        self.graph_bytes=0
        self.packet_rows=PacketMap(self,True);self.packet_map=PacketMap(self)
    def __len__(self):return self.db.execute('SELECT count(*) FROM fields').fetchone()[0]
    def __iter__(self):
        for (data,) in self.db.execute('SELECT data FROM fields ORDER BY ordinal'):yield json.loads(data)
    def rows_of_types(self,types):
        values=tuple(types)
        if not values:return
        for (data,) in self.db.execute('SELECT data FROM fields WHERE type IN ('+','.join('?' for _ in values)+') ORDER BY ordinal',values):yield json.loads(data)
    def __getitem__(self,key):
        if isinstance(key,slice):
            start,stop,step=key.indices(len(self))
            if step!=1:raise ValueError('Only contiguous disk slices supported')
            return [json.loads(r[0]) for r in self.db.execute('SELECT data FROM fields WHERE ordinal>? AND ordinal<=? ORDER BY ordinal',(start,stop))]
        if key<0:key+=len(self)
        value=self.db.execute('SELECT data FROM fields WHERE ordinal=?',(key+1,)).fetchone()
        if value is None:raise IndexError(key)
        return json.loads(value[0])
    def context_table(self, roles, associations):return Context(self,associations)
    def guard_graph(self,value):
        self.graph_bytes+=len(json.dumps(value,ensure_ascii=False).encode('utf-8'))
        if self.graph_bytes>large.DEFAULTS['max_model_bytes']:
            raise large.ResourceLimit('Bounded candidate context budget exceeded; complete indexed rows and associations retained')
    def count_types(self,types):
        return self.db.execute('SELECT count(*) FROM fields WHERE type IN ('+','.join('?' for _ in types)+')',tuple(types)).fetchone()[0]
    def close(self):self.db.close()


class Context(Sequence):
    def __init__(self,fields,requests):self.fields,self.requests=fields,requests
    @property
    def packet_rows(self):return self.fields.packet_rows
    def __len__(self):return len(self.fields)
    def __getitem__(self,key):
        if isinstance(key,slice):
            span=range(*key.indices(len(self)))
            if len(span)>4096:raise large.ResourceLimit('Single displayed evidence span exceeds 4096 rows; complete rows remain in the disk index')
            values=[]
            for i in span:
                row=self[i];self.fields.guard_graph(row);values.append(row)
            return values
        import g2b_associate as g2
        f=self.fields[key];role=g2.classify(f);association=None
        if role['role']==g2.NON_POSTED_REQUEST:
            q=self.requests.packet_map[f['packet_index']]
            if len(q['completions'])>GRAPH_ROWS:raise large.ResourceLimit('Single context association exceeds bounded graph budget; full association is in SQLite')
            packets=[c['packet_index'] for c in q['completions']]
            association=dict(outcome=q['outcome'],completion_packets=packets)
        elif role['role']==g2.COMPLETION_CANDIDATE:
            found=self.fields.db.execute('SELECT request FROM completions WHERE packet=?',(f['packet_index'],)).fetchone()
            association=dict(associated_request_packet=found[0] if found else None)
        previous=self.fields[key-1]['packet_index'] if key else None
        return dict(row=f['row'],packet_index=f['packet_index'],packet_gap_from_previous_tlp_row=None if previous is None else f['packet_index']-previous,
            time_display=f['time_display'],channel=f['channel'],tlp_type_hex=f['tlp_type_hex'],vendor_type_name=role['vendor_type_name'],role=role['role'],
            requester_bdf=g2.bdf(f['requester_id']),tag=f['tag'],completer_bdf=g2.bdf(f['completer_id']),compl_status=f['compl_status'],
            compl_status_name=None if f['compl_status'] is None else g2.STATUS_NAMES.get(f['compl_status'],'UNKNOWN'),association=association)


class CompletionRows(Sequence):
    def __init__(self,requests,index,count=None,channel=None):
        self.requests,self.index,self.count,self.channel=requests,index,count,channel
    def __len__(self):
        if self.count is not None:return self.count
        return self.requests.db.execute('SELECT count(*) FROM completions WHERE request=?',(self.index,)).fetchone()[0]
    def __iter__(self):
        for packet,data in self.requests.db.execute('SELECT c.packet,f.data FROM completions c LEFT JOIN fields f ON f.packet=c.packet WHERE c.request=? ORDER BY c.packet',(self.index,)):
            if data is None:raise KeyError(packet)
            yield self.requests.completion(packet,self.index,field=json.loads(data),request_channel=self.channel)
    def __getitem__(self,index):
        if index<0:index+=len(self)
        found=self.requests.db.execute('SELECT packet FROM completions WHERE request=? ORDER BY packet LIMIT 1 OFFSET ?',(self.index,index)).fetchone()
        if not found:raise IndexError(index)
        return self.requests.completion(found[0],self.index)


class RequestMap(Mapping):
    def __init__(self,requests):self.requests=requests
    def __len__(self):return len(self.requests)
    def __iter__(self):
        for (packet,) in self.requests.db.execute('SELECT packet FROM requests ORDER BY packet'):yield packet
    def __getitem__(self,packet):
        import g2b_associate as g2
        meta=self.requests.db.execute('SELECT r.next_request,r.completion_count,f.data FROM requests r LEFT JOIN fields f ON f.packet=r.packet WHERE r.packet=?',(packet,)).fetchone()
        if meta is None:raise KeyError(packet)
        if meta[2] is None:raise KeyError(packet)
        return self.from_record(packet,meta,json.loads(meta[2]))
    def from_record(self,packet,meta,f):
        import g2b_associate as g2
        role=g2.classify(f)
        value={k:f[k] for k in ('row','packet_index','time_display','channel','tlp_type_hex','requester_id','tag')}
        value.update(vendor_type_name=role['vendor_type_name'],requester_bdf=g2.bdf(f['requester_id']),
            outcome=g2.REISSUED if meta[0] is not None else g2.COMPLETIONS_OBSERVED if meta[1] else g2.NONE_OBSERVED,
            completions=CompletionRows(self.requests,packet,meta[1],f['channel']))
        if meta[0] is not None:value['reissued_at_packet']=meta[0]
        return value


class Requests(Sequence):
    def __init__(self,fields):self.fields,self.db=fields,fields.db;self.packet_map=RequestMap(self)
    def __len__(self):return self.db.execute('SELECT count(*) FROM requests').fetchone()[0]
    def __iter__(self):
        for packet,nxt,count,data in self.db.execute('SELECT r.packet,r.next_request,r.completion_count,f.data FROM requests r LEFT JOIN fields f ON f.packet=r.packet ORDER BY r.packet'):
            if data is None:raise KeyError(packet)
            yield self.packet_map.from_record(packet,(nxt,count),json.loads(data))
    def __getitem__(self,index):
        row=self.db.execute('SELECT packet FROM requests ORDER BY packet LIMIT 1 OFFSET ?',(index,)).fetchone()
        if not row:raise IndexError(index)
        return self.packet_map[row[0]]
    def completion(self,packet,request=None,field=None,request_channel=None):
        import g2b_associate as g2
        f=self.fields.packet_map[packet] if field is None else field;role=g2.classify(f)
        value={k:f[k] for k in ('row','packet_index','time_display','channel','tlp_type_hex','requester_id','tag','completer_id','compl_status')}
        value.update(vendor_type_name=role['vendor_type_name'],type_evidence=role['type_evidence'],completer_bdf=g2.bdf(f['completer_id']),compl_status_name=g2.STATUS_NAMES.get(f['compl_status'],'UNKNOWN'))
        if request is None:value['association']=g2.ORPHAN
        else:
            channel=self.fields.packet_map[request]['channel'] if request_channel is None else request_channel
            value.update(packet_gap_from_request=packet-request,direction_relation='opposite' if f['channel']!=channel else 'same')
        return value
    def lineage_end(self,q):
        packet=self.db.execute('SELECT terminal FROM requests WHERE packet=?',(q['packet_index'],)).fetchone()[0]
        return self.packet_map[packet]
    def lineage_counts(self):
        return {p:n for p,n in self.db.execute('SELECT terminal,count(*) FROM requests WHERE next_request IS NOT NULL GROUP BY terminal')}


def associate(db,root):
    """Same G2b key and capture-order semantics; outstanding state spills to disk."""
    import g2b_associate as g2
    db.executescript('''CREATE TABLE requests(packet INTEGER PRIMARY KEY,next_request INTEGER,completion_count INTEGER NOT NULL DEFAULT 0,terminal INTEGER);
        CREATE TABLE completions(packet INTEGER PRIMARY KEY,request INTEGER);
        CREATE INDEX completion_request ON completions(request,packet);
        CREATE TABLE latest(requester INTEGER,tag INTEGER,packet INTEGER,PRIMARY KEY(requester,tag));''')
    def guard(n):
        if n%512==0:
            if (root/'cancel.json').exists():raise InterruptedError('Cancelled during indexed associations')
            large.check_disk(root)
    for n,(data,) in enumerate(db.execute('SELECT data FROM fields ORDER BY ordinal')):
        guard(n)
        f=json.loads(data);role=g2.classify(f)['role'];key=f['requester_id'],f['tag'];packet=f['packet_index']
        if role not in (g2.NON_POSTED_REQUEST,g2.COMPLETION_CANDIDATE):continue
        prior=db.execute('SELECT packet FROM latest WHERE requester=? AND tag=?',key).fetchone()
        if role==g2.NON_POSTED_REQUEST:
            if prior:db.execute('UPDATE requests SET next_request=? WHERE packet=? AND completion_count=0',(packet,prior[0]))
            db.execute('INSERT INTO requests(packet) VALUES(?)',(packet,))
            db.execute('INSERT OR REPLACE INTO latest VALUES(?,?,?)',(*key,packet))
        else:
            db.execute('INSERT INTO completions VALUES(?,?)',(packet,prior[0] if prior else None))
            if prior:db.execute('UPDATE requests SET completion_count=completion_count+1 WHERE packet=?',prior)
    # Backwards traversal memoizes every reissue chain in O(n), independent of batch boundaries.
    for n,(packet,nxt) in enumerate(db.execute('SELECT packet,next_request FROM requests ORDER BY packet DESC')):
        guard(n)
        terminal=db.execute('SELECT terminal FROM requests WHERE packet=?',(nxt,)).fetchone()[0] if nxt is not None else packet
        db.execute('UPDATE requests SET terminal=? WHERE packet=?',(terminal,packet))
    db.commit()


def ingest(root,total,batch_size=512):
    """Validate every raw row against the existing grammars and cross-probe identity."""
    import verify_g1b_rows as g1
    import verify_g2a_fields as g2
    import verify_g3c0_messages as g3
    from verify_g1a_log import DONE_MARKER,RUNTIME_ERROR_RE,check_log
    root=Path(root);partial=root/'transactions.sqlite.partial'
    if partial.exists() or (root/'transactions.sqlite').exists():raise FileExistsError(partial)
    db=connect(partial)
    db.executescript('CREATE TABLE rows(ordinal INTEGER PRIMARY KEY,packet INTEGER UNIQUE,data TEXT); CREATE TABLE fields(ordinal INTEGER PRIMARY KEY,packet INTEGER UNIQUE,type INTEGER,data TEXT); CREATE TABLE messages(ordinal INTEGER PRIMARY KEY,packet INTEGER UNIQUE,data TEXT);')
    summary=check_log((root/'count.txt').read_text(encoding='utf-8'))
    if summary['tlp_callback_count']!=total:raise ValueError('Count binding mismatch')
    def lines(name,prefix,header,row_re,end_re):
        headers=done=seen=0;ended=False
        with (root/(name+'.txt')).open(encoding='utf-8-sig') as f:
            while line:=f.readline(large.MIB+1):
                if len(line)>large.MIB:raise large.ResourceLimit('Oversized decoder line')
                line=line.strip()
                if RUNTIME_ERROR_RE.search(line):raise ValueError('Native runtime error')
                if line==DONE_MARKER:done+=1
                if header(line):headers+=1;continue
                if not line.startswith(prefix):continue
                if ended:raise ValueError('Row after END')
                m=row_re.fullmatch(line)
                if m:
                    if headers!=1:raise ValueError('Row outside header')
                    seen+=1;yield seen,m
                    if seen%batch_size==0:
                        if (root/'cancel.json').exists():raise InterruptedError('Cancelled during index ingestion')
                        large.check_disk(root);db.commit()
                elif m:=end_re.fullmatch(line):
                    ended=True
                    if name=='rows' and (int(m['rows'])!=total or m['reason']!='trace_end'):raise ValueError('Incomplete row export')
                    if name=='fields' and int(m['rows'])!=total:raise ValueError('Incomplete field export')
                    if name=='messages' and (int(m['tlps'])!=total or int(m['messages'])!=seen):raise ValueError('Incomplete message export')
                else:raise ValueError('Unrecognized '+name+' record')
        if headers!=1 or done!=1 or not ended:raise ValueError('Missing or duplicate header/END/DONE in '+name)
        expected=total if name!='messages' else db.execute('SELECT count(*) FROM fields WHERE type IN (13,14,15,16)').fetchone()[0]
        if seen!=expected:raise ValueError('Wrong exported row count: '+name)
    def row_header(line):
        m=g1.HEADER_RE.fullmatch(line)
        if m and int(m['cap'])!=g1.FULL_EXPORT_CAP:raise ValueError('Dense input requires natural trace-end export')
        return bool(m)
    previous=-1
    try:
        for n,m in lines('rows','PCIE_G1B_',row_header,g1.ROW_RE,g1.END_RE):
            packet=int(m['index'])
            if packet<=previous or m['family']!='TLP' or int(m['width'])<1:raise ValueError('Invalid/unordered TLP row')
            if n==1 and packet!=summary['first_tlp_index']:raise ValueError('First index mismatch')
            previous=packet
            value=dict(row=n,packet_index=packet,time_display=m['time'].strip(),event_family=m['family'],channel=m['channel'].strip(),tlp_type_hex='0x'+m['type'][2:].upper(),link_width=int(m['width']))
            db.execute('INSERT INTO rows VALUES(?,?,?)',(n,packet,json.dumps(value,separators=(',',':'))))
        if previous!=summary['last_tlp_index']:raise ValueError('Last index mismatch')
        for n,m in lines('fields','PCIE_G2A_',lambda l:l==g2.HEADER,g2.ROW_RE,g2.END_RE):
            value=dict(row=n,packet_index=int(m['index']),time_display=m['time'].strip(),channel=m['channel'].strip(),tlp_type_hex='0x'+m['type'][2:].upper(),
                tag=None if m['tag']=='NA' else int(m['tag']),requester_id=None if m['requester']=='NA' else int(m['requester'],16),completer_id=None if m['completer']=='NA' else int(m['completer'],16),compl_status=None if m['status']=='NA' else int(m['status']))
            ref=db.execute('SELECT data FROM rows WHERE ordinal=?',(n,)).fetchone()
            reference=json.loads(ref[0]) if ref else None
            if reference is None or any(value[k]!=reference[k] for k in ('packet_index','time_display','channel','tlp_type_hex')):raise ValueError('G1/G2 row mismatch')
            db.execute('INSERT INTO fields VALUES(?,?,?,?)',(n,value['packet_index'],int(value['tlp_type_hex'],16),json.dumps(value,separators=(',',':'))))
        for n,m in lines('messages','PCIE_G3C0_',lambda l:l==g3.HEADER,g3.ROW_RE,g3.END_RE):
            code=None if m['code']=='NA' else int(m['code'],16);route=None if m['route']=='NA' else int(m['route'],16)
            value=dict(packet_index=int(m['index']),time_display=m['time'].strip(),channel=m['channel'].strip(),tlp_type_hex='0x'+m['type'][2:].upper(),requester_id=None if m['requester']=='NA' else int(m['requester'],16),message_code=code,message_code_name=None if code is None else g3.MESSAGE_CODE_NAMES.get(code,'UNMAPPED'),message_route=route,message_route_name=None if route is None else g3.MESSAGE_ROUTE_NAMES.get(route,'UNMAPPED'))
            ref=db.execute('SELECT data FROM fields WHERE type IN (13,14,15,16) AND packet=?',(value['packet_index'],)).fetchone()
            reference=json.loads(ref[0]) if ref else None
            if reference is None or any(value[k]!=reference[k] for k in ('packet_index','time_display','channel','tlp_type_hex','requester_id')):raise ValueError('Message/G2 row mismatch')
            if n>1 and value['packet_index']<=last_message:raise ValueError('Unordered messages')
            last_message=value['packet_index']
            db.execute('INSERT INTO messages VALUES(?,?,?)',(n,value['packet_index'],json.dumps(value,separators=(',',':'))))
        db.commit();associate(db,root)
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity failure')
    finally:db.close()
    partial.rename(root/'transactions.sqlite')
    return root/'transactions.sqlite'

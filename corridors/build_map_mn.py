import csv,json,re
R=[x for x in csv.DictReader(open('data/raw/segment_catalog.csv')) if x['from_lat'] and x['to_lat']]
SEEN=sorted({x['route_type'] for x in R})
KEEP={'Local','Limited','SBS'}
def on(s): return re.sub(r'\s+',' ',s.split('/')[0]).strip()
MN=dict(lat=(40.70,40.882),lon=(-74.02,-73.90))
def inbox(lat,lon,b):
    return b['lat'][0]<=lat<=b['lat'][1] and b['lon'][0]<=lon<=b['lon'][1]
def pick(streets,box,axis=None,lim=None,minfrac=0.3):
    out={}
    for x in R:
        if x['route_type'] not in KEEP: continue
        if on(x['from_stop']) not in streets or on(x['to_stop']) not in streets: continue
        pts=[(float(x['from_lat']),float(x['from_lon'])),(float(x['to_lat']),float(x['to_lon']))]
        if not all(inbox(a,b,MN) and inbox(a,b,B()) for a,b in pts): continue
        frac=1.0
        if axis is not None:
            i=0 if axis=='lat' else 1
            a,b=sorted((pts[0][i],pts[1][i]))
            ov=max(0,min(b,lim[1])-max(a,lim[0]))
            frac=ov/(b-a) if b>a else (1.0 if lim[0]<=a<=lim[1] else 0.0)
            if frac<minfrac: continue
        x=dict(x,frac=round(frac,2))
        k=(x['route_id'],x['direction'],x['timepoint_stop_id'],x['next_timepoint_stop_id'])
        out[k]=x
    return sorted(out.values(),key=lambda x:(x['route_id'],x['direction'],-float(x['from_lat'])))
def B(lat=(40.70,40.882),lon=(-74.02,-73.90)): return dict(lat=lat,lon=lon)
LEX=['LEXINGTON AV']
C=[
 (12,'125th St',['W 125 ST','E 125 ST'],None,None,'125th St in Manhattan, full length (Riverside Dr to the 3rd Ave/Triborough approach)','All stops on W 125 ST / E 125 ST; no clipping.','mapped','Only M125 has consecutive timepoints both named 125 ST; segments toward Riverside/Bronx end on other streets and are excluded by the both-stops rule.'),
 (13,'Lexington Ave (95th-125th St)',LEX,'lat',(40.7841,40.8045),'Lexington Ave between 95th St and 125th St','Clipped by latitude 40.7841-40.8045 (95th St = ~40.7841, 125th St = ~40.8043).','mapped','Southbound only in catalog (northbound runs on 3rd Ave/Madison). Lat bounds approximate (+/- a block). Segment 96th->68th (8% inside) excluded.'),
 (14,'116th St',['W 116 ST','E 116 ST'],None,None,'116th St in Manhattan, full length (M116)','No clipping; only segments with both timepoints on W/E 116 ST.','partial','Plan names "116th Street, Manhattan Avenue, Morningside Avenue, and Pleasant Avenue" (10 routes, 65,000 riders). Only 116th St proper is mapped; the other three connector streets have no stated extents so are not mapped (assumption). Routes other than M116 that use 116th St with sparse timepoints may be missing.'),
 (15,'79th St',['W 79 ST','E 79 ST'],'lon',(-73.9845,-73.9440),'79th St from Riverside Dr to East End Ave (M79 SBS)','Clipped by longitude -73.9845 (Riverside Dr) to -73.9440 (East End Ave).','mapped','Plan: 1.65 miles of the M79 SBS route.'),
 (17,'34th St Busway',['W 34 ST','E 34 ST'],'lon',(-73.9975,-73.9778),'34th St from 3rd Ave to 9th Ave (M34 / M34A SBS)','Segments on 34th St overlapping 9th Ave (lon -73.9975) to 3rd Ave (lon -73.9778) by >=30% of segment length.','partial','Timepoints are 5-10 avenues apart so segments straddle the limits (e.g. 12 Av->7 Av, 7 Av->2 Av); each segment carries overlap_frac. Segments ending on MARGINAL ST/FERRY/WATERSIDE excluded (not on 34th St).'),
 (18,'9th Avenue',['9 AV'],'lat',(40.7507,40.7644),'9th Ave from 32nd St to 50th St (M11)','Segments on 9 AV (Manhattan) overlapping lat 40.7507-40.7644 by >=30%.','partial','Only M11 southbound (42nd->23rd St) has consecutive 9 AV timepoints; it straddles the 32nd St limit (overlap_frac given). 49 AV (Queens) excluded by exact name+location. Northbound M11 runs on 10th Ave and is not on 9th Ave.'),
 (19,'Lexington Ave (52nd-60th St)',LEX,'lat',(40.7571,40.7625),'Lexington Ave between 52nd St and 60th St','Segments on LEXINGTON AV overlapping lat 40.7571-40.7625 by >=30%.','partial','Timepoints are sparse (59th->42nd St straddles both limits, overlap_frac ~0.45). Southbound only. Plan cites eight routes (70,000 riders) but catalog has only M101/M102/M103 consecutive Lex timepoints here; other routes may use different timepoints. Weak definition.'),
 (20,'6th Ave',['6 AV'],'lat',(40.7195,40.7645),'6th Ave (Avenue of the Americas) from Lispenard St to 59th St','Segments on 6 AV overlapping lat 40.7195-40.7645 (Lispenard St ~40.7195, 59th St ~40.7645) by >=30%.','mapped','Northbound only in catalog. 56 AV / 36 AV (Queens) excluded by exact name. Stops spelled "AVENUE OF THE AMERICAS" do not match "6 AV" and are excluded.'),
 (21,'Madison Ave',['MADISON AV'],'lat',(40.7415,40.7525),'Madison Ave from 23rd St to 42nd St','Segments on MADISON AV overlapping lat 40.7415-40.7525 by >=30%.','partial','Northbound only (M1-M4). Long timepoint spacing: 28th->58th St and 32nd->57th St straddle the 42nd St limit (overlap_frac 0.36-0.45), so miles overstate the corridor stretch. MADISON ST (Brooklyn/Lower Manhattan) excluded by exact name.'),
]
UN=[(11,'Upper Manhattan North-South','Plan text only lists this corridor name in the Priority Corridors table (and map); no streets, endpoints or routes are given. No defensible definition without guessing. No web search used.'),
    (16,'Midtown Crosstown','Plan text only lists the name; no streets, endpoints or routes described. Could overlap with 34th/42nd/57th St corridors but not stated, so not guessed. No web search used.'),
    (22,'Broadway','Plan defines Broadway from 14th St to Houston St, but the catalog has no segment with both timepoints on BROADWAY there: the only timepoint named on Broadway is BROADWAY/WEST HOUSTON ST (M55 southbound, which then runs south of Houston). Routes M1/M2/M3 near Broadway use stop names like "4 AV/E 10 ST" which do not name Broadway, so were not guessed. No web search used.')]
if __name__=='__main__':
    out=[]
    for id_,name,streets,axis,lim,defn,ext,status,notes in C:
        segs=pick(streets,None,axis,lim)
        if any(s['frac']<1 for s in segs) and status=='mapped': status='partial'
        out.append(dict(id=id_,name=name,borough='MN',status=status if segs else 'unmapped',definition=defn,on_streets=streets,extent=ext,
          routes=sorted({s['route_id'] for s in segs}),
          segments=[dict(route_id=s['route_id'],direction=s['direction'],from_id=s['timepoint_stop_id'],to_id=s['next_timepoint_stop_id'],from_stop=s['from_stop'],to_stop=s['to_stop'],miles=round(float(s['miles']),3),overlap_frac=s['frac'],from_lat=float(s['from_lat']),from_lon=float(s['from_lon']),to_lat=float(s['to_lat']),to_lon=float(s['to_lon'])) for s in segs],notes=notes))
    for id_,name,why in UN:
        e=dict(id=id_,name=name,borough='MN',status='unmapped',definition='',on_streets=[],extent='',routes=[],segments=[],notes=why)
        if id_==22: e['definition']='Broadway from 14th St to Houston St (per plan)'; e['on_streets']=['BROADWAY']; e['extent']='14th St to Houston St'
        out.append(e)
    out.sort(key=lambda c:c['id'])
    json.dump(dict(route_types_seen=SEEN,route_types_kept=sorted(KEEP),corridors=out),open('corridors/map_mn.json','w'),indent=1)

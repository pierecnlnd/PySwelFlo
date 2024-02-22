from csggeom import *
from feedpts import *
from wellhead import *
from swfinput import *

# ADD WELLHEAD CONDITIONS
# -----------------------

wh = Welllhead()
wh.add_cond(
    wh_p=15.93,
    wh_Q=20,
    wh_T=170.43,
    wh_xCO2=0.001
)
wh.pre_process_wellhead()
# print(wh.wellhead)

# ADD CASING GEOMETRY
# -------------------

csg = CsgGeom()
csg.add_section(
    elev=-9999,
    sec_len=750,
    angle_vert=90,
    vert_ext=750,
    subdiv_len=20,
    type='CASING',
    outerdiam=9.625
)
csg.add_section(
    elev=-9999,
    sec_len=300,
    angle_vert=90,
    vert_ext=300,
    subdiv_len=20,
    type='LINER',
    outerdiam=7
)
csg.pre_process_csggeom()
# print(csg.csggeom)

# ADD FEED POINTS
# -------------------

feed = FeedPts()
feed.add_points(
    depth=1000,
    type='fixed Q',
    res_p=55,
    res_T=270,
    res_xCO2=.3e-3,
    Q=20
)
feed.pre_process_feedpts()
# print(feed.feedpts)

swfinput = SWFinput(
    wellhead=wh,
    csggeom=csg,
    feedpts=feed
)
swfinput.pre_process_swfinput()
print(swfinput.swfinput)

swfinput.write_input(dir = os.getcwd()+'\\trial')
swfinput.run('C:\\Users\\piere\\Kerjaan\\PGE\\Tugas - Couple wellbore reservoir model\\SwelFloPackage1')
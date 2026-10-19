"""Optional offline RoboDK bridge using the downloaded KR360 model.

Requires RoboDK installed locally and `pip install robodk numpy`.
Always simulation; never connects to a controller or generates machine code.
This bridge is not runtime-tested because RoboDK is not installed here.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from robotics.assembly import factory_scene
from robotics.core import read_json,GEOMETRY,ROOT

def run():
    from robodk.robolink import Robolink,RUNMODE_SIMULATE,ITEM_TYPE_ROBOT
    from robodk.robomath import Mat,transl
    rdk=Robolink();rdk.setRunMode(RUNMODE_SIMULATE)
    station=rdk.AddStation('AI-DFab KR360 offline assembly')
    robot=rdk.AddFile(str(ROOT/'robotics/assets/KUKA-KR-360-R2830.robot'),station)
    if not robot.Valid() or robot.Type()!=ITEM_TYPE_ROBOT:raise RuntimeError('KR360 model could not be loaded')
    robot.setPoseFrame(Mat(np.eye(4).tolist()))
    robot.setPoseTool(transl(0,0,200))
    robot.setSpeed(50);robot.setSpeedJoints(10)
    data=factory_scene(read_json(GEOMETRY))
    def pose(pos,R):
        m=np.eye(4);m[:3,:3]=R;m[:3,3]=pos;return Mat(m.tolist())
    for i,p in enumerate(data['parts']):
        vertices=np.asarray(p['v']);triangles=vertices[np.asarray(p['f'])].reshape(-1,3).T
        plate=rdk.AddShape(Mat(triangles.tolist()),add_to=None)
        plate.setName(p['id']);plate.setColor([.72,.24,.2,1])
        target=np.asarray(p['target']);frame=np.asarray(p['frame']);normal=frame[:,2]
        stack=np.array([750.,-1750.,600+(len(data['parts'])-1-i)*32])
        pickup_frame=np.array([[0,-1,0],[1,0,0],[0,0,1.]])
        plate.setPose(pose(stack,pickup_frame))
        # Demonstration waypoints, not Manis-computed insertion constraints.
        points=[(stack+[0,0,400],pickup_frame,False),(stack,pickup_frame,False),
                (stack+[0,0,900],pickup_frame,True),(target+normal*420,frame,True),
                (target,frame,True),(target+normal*350,frame,False)]
        for j,(pos,F,carry) in enumerate(points):
            n=F[:,2];x=F[:,0];z=-n;y=np.cross(z,x);toolR=np.column_stack([x,y,z])
            target_pose=pose(pos+n*55,toolR)
            solution=robot.SolveIK(target_pose)
            if len(solution.list())<6:raise RuntimeError(f'{p["id"]} waypoint {j}: no IK solution; revise fixture placement')
            start=robot.Joints()
            collision=robot.MoveJ_Test(start,solution)
            robot.setJoints(start)
            if collision!=0:raise RuntimeError(f'{p["id"]} waypoint {j}: motion test failed ({collision})')
            # Use RoboDK's simulation object attachment for the transport sequence.
            if j==2:
                plate.setParentStatic(robot)
            if j==5:
                plate.setParentStatic(station);plate.setPose(pose(target,frame))
            robot.MoveJ(solution)
        plate.setParentStatic(station);plate.setPose(pose(target,frame))
    print('Offline sequence complete. Joint insertion, tool collision geometry and physical loads remain unvalidated.')

if __name__=='__main__':run()

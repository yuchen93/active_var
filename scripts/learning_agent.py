#!/usr/bin/env python
from hlpr_single_plane_segmentation.srv import *
from ar_track_alvar_msgs.msg import AlvarMarkers
from active_var.msg import *
from active_var.srv import *
import rospy
import math
import tf
import tf2_ros
import tf2_geometry_msgs
from geometry_msgs.msg import Pose
from hlpr_manipulation_utils.arm_moveit2 import *
from hlpr_manipulation_utils.manipulator import Gripper
from add_collision_objects import *

GRID_WORLD_WIDTH = 6
GRID_WORLD_HEIGHT = 4

ACTIONS = {'UP':0, 'DOWN':1, 'LEFT':2, 'RIGHT':3, 'STAY':4 }

x_side = 0.1
y_side = 0.1

markers = {}

tfBuffer = tf2_ros.Buffer()       
listener=tf2_ros.TransformListener(tfBuffer)
features = {} # [is_goal[marker8], is_init[purple], is_black[black]]

arm = ArmMoveIt(planning_frame='linear_actuator_link', _arm_name='right')
gripper = Gripper(prefix='right')

def get_next_state(state, action):
    next_state = state
    if action == ACTIONS['UP']:
        next_state = state - GRID_WORLD_WIDTH
    if action == ACTIONS['DOWN']:
        next_state = state + GRID_WORLD_WIDTH
    if action == ACTIONS['LEFT']:
        next_state = state - 1
    if action == ACTIONS['RIGHT']:
        next_state = state + 1
    return next_state

def collect_visual_demo(typed=False):
    rospy.loginfo("Collecting visual demonstrations")
    states = []
    actions = []
    
    if not typed:
		printed = False
		while not (7 in markers):
		    if not printed:
		        rospy.loginfo("Waiting for marker 7 ...")
		        printed = True
		option = int(input('Enter 1 to record demo, 0 to end:'))
		while option != 0:
		    transform = tfBuffer.lookup_transform('ar_marker_0','ar_marker_7',rospy.Time(0), rospy.Duration(1.0))
		    ps = geometry_msgs.msg.PoseStamped()
		    ps.header.stamp = rospy.Time.now()
		    ps.header.frame_id = 'ar_marker_7'
		    pt = tf2_geometry_msgs.do_transform_pose(ps, transform)
		    pt.header.stamp = rospy.Time.now()
		    pt.header.frame_id = 'ar_marker_0'
		    x = pt.pose.position.x
		    y = pt.pose.position.y
		    curr_state = get_state(x, y)
		    states.append(curr_state)
		    rospy.loginfo('state recorded: '+str(curr_state))
		    option = int(input('Enter 1 to record demo, 0 to end:'))
    else:
        option = int(input('Enter state or -1 to exit:'))
        while option != -1:
		    curr_state = option
		    states.append(curr_state)
		    rospy.loginfo('state recorded: '+str(curr_state))
		    option = int(input('Enter state or -1 to exit:'))
    	   	  
    for i in range(len(states)-1):
    	if states[i+1] == states[i]:
    	    actions.append(ACTIONS['STAY'])
    	elif states[i+1] == states[i] + 1:
    		actions.append(ACTIONS['RIGHT'])
    	elif states[i+1] == states[i] - 1:
    		actions.append(ACTIONS['LEFT'])
    	elif states[i+1] == states[i] + GRID_WORLD_WIDTH:
    		actions.append(ACTIONS['DOWN'])
    	elif states[i+1] == states[i] - GRID_WORLD_WIDTH:
    		actions.append(ACTIONS['UP'])
    	else:
    		actions.append(-1)
    		print("[ERROR finding action] state:",states[i+1],"is not right next to",states[i])
    		
    print "demos:",states,actions
    return [(states[i], actions[i]) for i in range(len(actions))]

def update_marker_pose(data):
    for marker in data.markers:
        curr_pose = marker.pose.pose.position
        if marker.id in markers:
            markers[marker.id].x += curr_pose.x
            markers[marker.id].y += curr_pose.y
            markers[marker.id].z += curr_pose.z
            markers[marker.id].x /= 2
            markers[marker.id].y /= 2
            markers[marker.id].z /= 2
        else:
            markers[marker.id] = curr_pose

def get_state_center(state):
    global x_side, y_side, num_states
    x = (GRID_WORLD_HEIGHT - state//GRID_WORLD_WIDTH)*x_side - x_side
    y = (GRID_WORLD_WIDTH-state%GRID_WORLD_WIDTH)*y_side - y_side
    return (x,y)

def get_state(x,y):
    global x_side, y_side, num_states
    print("x=",x,", y=",y)
    state = num_states - 1 - (int(math.floor(2*(x+x_side/2)/x_side))//2*GRID_WORLD_WIDTH 
                                + int(math.floor(2*(y+y_side/2)/y_side))//2)
    return int(state)

def distance2D(point1, point2):
    return math.sqrt((point1[0]-point2[0])**2+(point1[1]-point2[1])**2)

def distance(point1, point2):
    return math.sqrt((point1.x-point2.x)**2+(point1.y-point2.y)**2+(point1.z-point2.z)**2)

def construct_world():
    #             marker1
    #
    #
    #
    #marker4      marker0
    global frames_client, x_side, y_side, num_states, features
    rospy.sleep(1.0)
    printed = False
    while not (0 in markers):
        if not printed:
            rospy.loginfo("Waiting for marker 0 ...")
            printed = True
    rospy.loginfo("Constructing working environment ...")
    width = 0.5  #distance(markers[0],markers[4])
    height = 0.3 #distance(markers[0], markers[1])
    rospy.loginfo("workspace size:"+str(width)+" " +str(height))
    x_side = height / (GRID_WORLD_HEIGHT - 1)
    y_side = width / (GRID_WORLD_WIDTH - 1)
    rospy.loginfo("cell size:"+str(x_side)+" "+str(y_side))
    num_states = GRID_WORLD_WIDTH*GRID_WORLD_HEIGHT
    #parent_frames = ["ar_marker_0"]*num_states
    marker0_transform = tfBuffer.lookup_transform('linear_actuator_link','ar_marker_0',rospy.Time(0), rospy.Duration(1.0))
    ps = geometry_msgs.msg.PoseStamped()
    ps.header.stamp = rospy.Time.now()
    pt = tf2_geometry_msgs.do_transform_pose(ps, marker0_transform)
    pt.header.stamp = rospy.Time.now()
    pt.header.frame_id = 'linear_actuator_link'

    parent_frames = ["linear_actuator_link"]*num_states
    tf_frames_request = BroadcastObjectFramesRequest()
    tf_frames_request.parent_frames = parent_frames
    child_frames = []
    for frame in range(num_states):
        child_frames.append("state_"+str(frame))
    tf_frames_request.child_frames = child_frames
    poses = []
    for frame in range(num_states):
        pose = Pose()
        pose.position.x = pt.pose.position.x + x_side * ((num_states - 1 - frame) // GRID_WORLD_WIDTH)
        pose.position.y = pt.pose.position.y + y_side * ((num_states - 1 - frame) % GRID_WORLD_WIDTH)
        pose.position.z = pt.pose.position.z + 0.03
        pose.orientation.w = 1
        poses.append(pose)
    tf_frames_request.poses = poses
    tf_res = frames_client(tf_frames_request)
    if tf_res is False:
        rospy.logerr("Update failed")
        return False

    raw_input('Workspace constructed, press Enter to continue extracting features...')
    rospy.loginfo('Detecting Features ...')
    printed = False
    while not (8 in markers): #target
        if not printed:
            rospy.loginfo("Waiting for marker 8 ...")
            printed = True

    black_transform = tfBuffer.lookup_transform('state_'+str(num_states-1),'black',rospy.Time(0), rospy.Duration(1.0))
    ps = geometry_msgs.msg.PoseStamped()
    ps.header.stamp = rospy.Time.now()
    ps.header.frame_id = 'black'
    pt = tf2_geometry_msgs.do_transform_pose(ps, black_transform)
    pt.header.stamp = rospy.Time.now()
    pt.header.frame_id = 'state_'+str(num_states-1)
    black_x = pt.pose.position.x
    black_y = pt.pose.position.y
    black_state = get_state(black_x,black_y)
    rospy.loginfo('---> Balck center state: '+str(black_state))
    
    target_transform = tfBuffer.lookup_transform('state_'+str(num_states-1),'ar_marker_8',rospy.Time(0), rospy.Duration(1.0))
    ps = geometry_msgs.msg.PoseStamped()
    ps.header.stamp = rospy.Time.now()
    ps.header.frame_id = 'ar_marker_8'
    pt = tf2_geometry_msgs.do_transform_pose(ps, target_transform)
    pt.header.stamp = rospy.Time.now()
    pt.header.frame_id = 'state_'+str(num_states-1)
    target_x = pt.pose.position.x
    target_y = pt.pose.position.y
    target_state = get_state(target_x,target_y)

    rospy.loginfo('---> Target state: '+str(target_state))
    
    for state_i in range(GRID_WORLD_WIDTH*GRID_WORLD_HEIGHT):
        features[state_i] = [1.0,0.0,0.0]
        state_center = get_state_center(state_i)
        if distance2D(state_center, (black_x,black_y)) < 0.1:
             features[state_i][2] = 1.0
    features[target_state][1] = 1.0
    features[target_state][0] = 1.0
    	
    rospy.loginfo('Redeay to collect visual demos')
    return True

def grasp_cup():
    global arm, gripper
    target_transform = tfBuffer.lookup_transform('state_'+str(num_states-1),'purple',rospy.Time(0), rospy.Duration(15.0))
    ps = geometry_msgs.msg.PoseStamped()
    ps.header.stamp = rospy.Time.now()
    ps.header.frame_id = 'purple'
    pt = tf2_geometry_msgs.do_transform_pose(ps, target_transform)
    pt.header.stamp = rospy.Time.now()
    pt.header.frame_id = 'state_'+str(num_states-1)
    target_x = pt.pose.position.x
    target_y = pt.pose.position.y
    cup_state = get_state(target_x,target_y)

    transform = tfBuffer.lookup_transform('linear_actuator_link','purple',rospy.Time(0), rospy.Duration(15.0))
    ps = geometry_msgs.msg.PoseStamped()
    ps.header.stamp = rospy.Time.now()
    ps.header.frame_id = 'purple'
    pt = tf2_geometry_msgs.do_transform_pose(ps, transform)
    pt.header.stamp = rospy.Time.now()
    pt.header.frame_id = 'linear_actuator_link'
    pt.pose.orientation.x = 0.0
    pt.pose.orientation.y = 0.0
    pt.pose.orientation.z = 0.0
    pt.pose.orientation.w = 1
    pt.pose.position.z += 0.1
    pt.pose.position.x -= 0.15
    arm.move_to_ee_pose(pt)
    rospy.sleep(3)
    pt.pose.position.x += 0.05
    arm.move_to_ee_pose(pt)
    rospy.sleep(3)
    gripper.close(100)
    return cup_state

def point_at_state(state):
    global arm, gripper
    gripper.close(100)
    transform = tfBuffer.lookup_transform('linear_actuator_link','state_'+str(state),rospy.Time(0), rospy.Duration(1.0))
    ps = geometry_msgs.msg.PoseStamped()
    ps.header.stamp = rospy.Time.now()
    ps.header.frame_id = 'state_'+str(state)
    pt = tf2_geometry_msgs.do_transform_pose(ps, transform)
    pt.header.stamp = rospy.Time.now()
    pt.header.frame_id = 'linear_actuator_link'
    pt.pose.orientation.x = 0.006
    pt.pose.orientation.y = 0.692
    pt.pose.orientation.z = 0.065
    pt.pose.orientation.w = 0.719
    pt.pose.position.z += 0.18
    arm.move_to_ee_pose(pt)
    rospy.sleep(3)

def move_to_state(state):
    global arm
    transform = tfBuffer.lookup_transform('linear_actuator_link','state_'+str(state),rospy.Time(0), rospy.Duration(1.0))
    ps = geometry_msgs.msg.PoseStamped()
    ps.header.stamp = rospy.Time.now()
    ps.header.frame_id = 'purple'
    pt = tf2_geometry_msgs.do_transform_pose(ps, transform)
    pt.header.stamp = rospy.Time.now()
    pt.header.frame_id = 'linear_actuator_link'
    pt.pose.orientation.w = 1.0
    pt.pose.orientation.x = 0.0
    pt.pose.orientation.y = 0.0
    pt.pose.orientation.z = 0.0
    pt.pose.position.z += 0.1
    arm.move_to_ee_pose(pt)
    rospy.sleep(3)


def arm_homing():
    global arm
    jointTarget = [0.947, 5.015, 4.95, 1.144, 11.425, 4.870, 7.281]
    arm.move_to_joint_pose(jointTarget)
    rospy.sleep(3)

def acitve_var_learning_agent():
    global frames_client, features, arm
    rospy.init_node('acitve_var_learning_agent')

    env = collision_objects()
    env.publish_collision_objects()
    
    arm_homing()

    rospy.Subscriber("ar_pose_marker", AlvarMarkers, update_marker_pose)
    rospy.wait_for_service('broadcast_object_frames')
    frames_client = rospy.ServiceProxy("broadcast_object_frames", BroadcastObjectFrames)
    rospy.wait_for_service('active_var')
    active_var_client = rospy.ServiceProxy("active_var", ActiveVaRQuery )

    
    if not construct_world():
        rospy.logerr("Failed to construct environment")
        return 
    
    rospy.loginfo('Redeay to collect visual demos')
    iteration = 0
    demonstrations = []
    init_states = [6,17,19,22]
    while True:
        demos = collect_visual_demo(typed=True)
        for demo in demos:
            sa = StateAction()
            sa.state = demo[0]
            sa.action = demo[1]
            demonstrations.append(sa)
        active_var_request = ActiveVaRQueryRequest()
        active_var_request.demonstration = demonstrations
        active_var_request.width = GRID_WORLD_WIDTH
        active_var_request.height = GRID_WORLD_HEIGHT
        active_var_request.num_features = 3
        active_var_request.discount = 0.95
        active_var_request.confidence = 50 
        active_var_request.initial_states = init_states
        active_var_request.terminal_states = []
        active_var_request.alpha = 0.95
        active_var_request.epsilon = 0.05
        active_var_request.delta = 0.1
        active_var_request.state_features = [FloatVector(features[i]) for i in range(GRID_WORLD_WIDTH*GRID_WORLD_HEIGHT)]
        response = active_var_client(active_var_request)
        iteration += 1
        # execute current policy
        curr_policy = response.policy
        raw_input('Ready to execute current policy, press Enter to continue...')
        cup_state = grasp_cup()
        move_to_state(cup_state)
        while curr_policy[cup_state] != ACTIONS['STAY']:
            cup_state = get_next_state(cup_state,curr_policy[cup_state])
            print "moving to state ", cup_state
            move_to_state(cup_state)
        gripper.open(100)
        arm_homing()
        
        print "Iteration",iteration, " query:", response.query_state
        point_at_state(response.query_state)
        gripper.open(100)
        arm_homing()

if __name__ == "__main__":
    acitve_var_learning_agent()

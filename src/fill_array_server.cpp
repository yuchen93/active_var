#include "ros/ros.h"
#include "active_var/FillArray.h"
#include <string>
#include <vector>
#include <cstdlib>
#include <sstream>
#include "mdp.hpp"

using namespace std;

bool fillup(active_var::FillArray::Request  &req,
         active_var::FillArray::Response &res)
{
   

  //fill int64[size] with values
  vector<int> policy(req.size);
  for(int i=0; i<req.size; i++)
    policy[i] = req.value;
  res.policy = policy;
  ROS_INFO("request: size=%ld, value=%ld", (long int)req.size, (long int)req.value);
  stringstream ss;
  
    for(int i=0; i<req.size; i++)
    {
        ss << res.policy[i] << " ";
    }
    ROS_INFO("sending back response: %s", ss.str().c_str());
  return true;
}

int main(int argc, char **argv)
{
  ros::init(argc, argv, "fill_array_server");
  ros::NodeHandle n;

  ros::ServiceServer service = n.advertiseService("fill_array", fillup);
  ROS_INFO("Ready to fill array.");
  ros::spin();

  return 0;
}

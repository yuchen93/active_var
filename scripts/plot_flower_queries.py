#code to plot the queries for place flowers
import numpy as np
import matplotlib.pyplot as plt
import active_utils as autils

count = 0

def get_query_data(filename):
    f = open(filename)
    query = []
    demo = []
    obj_weights = []
    abs_weights = []
    var_obj_weights = []
    var_abs_weights = []
    state = ""
    for line in f:
        if line.startswith("#query"):
            state = "Query"
            continue
        elif line.startswith("#demo"):
            state = "Demo"
            continue
        elif line.startswith("#obj weights"):
            state = "ObjWeights"
            continue
        elif line.startswith("#abs weights"):
            state = "AbsWeights"
            continue
        elif line.startswith("#alpha obj weights"):
            state = "AlphaObj"
            continue
        elif line.startswith("#alpha abs weights"):
            state = "AlphaAbs"
            continue
        if state == "Query":
            line = line.split(",")
            query.append([float(l) for l in line])
        elif state == "Demo":
            line = line.split(",")
            demo = [float(l) for l in line]
        elif state == "ObjWeights":
            line = line.split(",")
            obj_weights = [float(l) for l in line]
        elif state == "AbsWeights":
            line = line.split(",")
            abs_weights = [float(l) for l in line]
        elif state == "AlphaObj":
            line = line.split(",")
            var_obj_weights = [float(l) for l in line]
        elif state == "AlphaAbs":
            line = line.split(",")
            var_abs_weights = [float(l) for l in line]


        #print(line)
    return np.array(query), np.array(demo), np.array(obj_weights), np.array(abs_weights), np.array(var_obj_weights), np.array(var_abs_weights)

def plot_table_demo(query, demo, title = ""):
    global count
    count += 1
    plt.subplot(6, 6, count)
    #plot placement of objects
    for i in range(len(query)):
        plt.plot(query[i,0], query[i,1], 'o', label="object " + str(i+1), markersize=10)
    #plot pi_map
    plt.plot(-1, -1, 'kv', markersize=10, label="MAP prediction")
    plt.plot(-1, -1, 's', markersize=10, label="0.95-VaR")
    plt.plot(demo[0], demo[1], '*', markersize=10, label="demo")

    plt.legend()
    plt.xticks([])
    plt.yticks([])
    plt.legend(bbox_to_anchor=(3, -2.5))
    plt.axis([0,1,0,1])
    plt.title(title)

def plot_table_heat_map(query, obj_weights, abs_weights, title = ""):
    global count
    count += 1
    plt.subplot(6, 6, count)
    zero_obj_weights = np.zeros(obj_weights.shape)
    table_rbf = autils.RbfComplexReward(query, zero_obj_weights, abs_weights)

    n = 50
    x = np.linspace(0., 1., n)
    y = np.linspace(1., 0., n)
    X, Y = np.meshgrid(x, y)

    Z = table_rbf.rbf_heat(X,Y)

    plt.pcolormesh(X, Y, Z, cmap = 'hot', vmin=-.2, vmax=.35)
    plt.colorbar()
    #plt.imshow(heatmap, cmap='hot')
    #plt.colorbar()
    plt.xticks([])
    plt.yticks([])
    plt.axis([0,1,0,1])
    plt.title(title)

def plot_object_heat_map(query, obj_weights, abs_weights, title = ""):
    global count
    count += 1
    plt.subplot(6, 6, count)
    zero_abs_weights = np.zeros(abs_weights.shape)
    obj_rbf = autils.RbfComplexReward(query, obj_weights, zero_abs_weights)

    n = 50
    x = np.linspace(0., 1., n)
    y = np.linspace(1., 0., n)
    X, Y = np.meshgrid(x, y)

    Z = obj_rbf.rbf_heat(X,Y)

    plt.pcolormesh(X, Y, Z, cmap = 'hot', vmin=-0.2, vmax=0.35)
    plt.colorbar()
    for c in obj_rbf.obj_centers:
        plt.plot(c[0],c[1],'o',markersize=10)
    #plt.imshow(heatmap, cmap='hot')
    #plt.colorbar()
    plt.xticks([])
    plt.yticks([])
    plt.axis([0,1,0,1])
    plt.title(title)


def plot_table_guess(query, demo, obj_weights, abs_weights, var_obj_weights, var_abs_weights, title = ""):
    global count
    count += 1
    plt.subplot(6, 6, count)
    #plot placement of objects
    for i in range(len(query)):
        plt.plot(query[i,0], query[i,1], 'o', label="object " + str(i+1), markersize=10)
    #plot pi_map
    query_rbf = autils.RbfComplexReward(query, obj_weights, abs_weights)
    pi_map, _ = query_rbf.estimate_best_placement()
    plt.plot(pi_map[0], pi_map[1], 'kv', markersize=10, label="MAP")
    var_rbf = autils.RbfComplexReward(query, var_obj_weights, var_abs_weights)
    pi_var, _ = var_rbf.estimate_best_placement()
    plt.plot(pi_var[0], pi_var[1], 's', markersize=10, label="$\alpha$-VaR")

    plt.plot(demo[0], demo[1], '*', markersize=10, label="demo")
    #plt.legend()
    plt.xticks([])
    plt.yticks([])
    plt.axis([0,1,0,1])
    plt.title(title)
if __name__=="__main__":
    #first parse out the data
    seed = 0
    filename = "./data/flowers_seed" + str(seed) + "_randomFalse_demo" + str(0) + ".txt"
    init_query, demo, obj_weights, abs_weights, _, _ = get_query_data(filename)
    #plot the table and demo
    plot_table_demo(init_query, demo, "Demo " + str(0))

    corner_query = np.array([[0.1, 0.9],[0.9, 0.9], [0.1, 0.1], [0.9, 0.1]])

    for d in range(1,11):
        #get previous query_info
        filename = "./data/flowers_seed" + str(seed) + "_randomFalse_demo" + str(d-1) + ".txt"
        query, demo, obj_weights, abs_weights, _, _ = get_query_data(filename)
        #plot pi_map (best guess of placement) given previous demos in query position
        filename_next = "./data/flowers_seed" + str(seed) + "_randomFalse_demo" + str(d) + ".txt"
        query_next, demo_next, obj_weights_next, abs_weights_next, var_obj_weights, var_abs_weights  = get_query_data(filename_next)
        #plot the table heat map of var_query
        plot_table_heat_map(query_next, var_obj_weights, var_abs_weights, "0.95-VaR Table Reward")
        plot_object_heat_map(corner_query, var_obj_weights, var_abs_weights, "0.95-VaR Object Reward")
        plot_table_guess(query_next, demo_next, obj_weights, abs_weights, var_obj_weights, var_abs_weights, "Query " + str(d)  )
    plt.show()

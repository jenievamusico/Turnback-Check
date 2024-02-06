# ===================================================================================================================================
# || Authors:   Michael Hui-Fumagalli (base itinerary.xml to .csv) and Jenieva Musico (.csv file to final turnback check ouput)    ||
# || Date:      Dec 15, 2023                                                                                                       ||
# || Version:   1.0                                                                                                                ||
# ===================================================================================================================================

#===== IMPORT =====
import xml.etree.ElementTree as ET
import pandas as pd
import easygui as gui
import os
import itertools
import time
import math


# ================ INITIALIZATION ================
cols = ["itinerary", "path", "route", "documentName", "vertexName", "vertexID", "neighbourID"]
rows = []

# ================ MICHAEL'S FUNCTIONS ================

# PURPOSE:  Provide a way to remove all selected nodes without using an absolute reference. Relative references are usable, unlike with remove() method. Function taken from https://stackoverflow.com/questions/39337042/elementtree-remove-element
# INPUT 1:  Tree element below which to search (usually 'root')
# INPUT 2:  Selection specified in XPath syntax (syntax can be found at https://docs.python.org/3/library/xml.etree.elementtree.html#supported-xpath-syntax)
# OUTPUT:  None
def removeall(root: ET.Element, match, namespaces=None):
    parent_by_child=dict(itertools.chain.from_iterable(
        ((child, element) for child in element) for element in root.iter()))

    for element in root.findall(match, namespaces):
        parent_by_child[element].remove(element)


# PURPOSE:  Search for nodes with matching tags and attributes, and copy them
# INPUT 1:  Tree element below which to search (usually a branch, such as "itineraries" or "vertices")
# INPUT 2:  Node to find matching data for (usually a node with no children)
# OUTPUTS:  First node of the same type as match (eg if match is a <vertex> under <routes>, output will be a <vertex> under <vertices>)
def searchNode(root: ET.Element, match: ET.Element):
    for branch in root:
        if ((branch.tag != match.tag + "s") and not(match.tag == "vertex" and branch.tag == "vertices")): 
            continue #continue to next branch if branch and node have tag mismatch
        else:
            for child in branch:
                if ((child.get("name") != match.get("name")) or (match.get("documentname") != child.get("documentname")) or (match.get("id") != child.get("id"))):
                    continue
                else: #Find the node with the same name, documentname and id
                    return child


# PURPOSE:  Shell function to hold pre-conversion removeall() function calls
# INPUT:    Tree element (usually root)
# OUTPUT:   None
def preConversionCleanup(root: ET.Element):
    removeall(root, ".//shuntings")
    removeall(root, ".//edges")
    removeall(root, ".//aspects")
    for node in root.findall(".//stationvertex"):
        node.tag = "vertex"


# PURPOSE:  Shell function to hold post-conversion removeall() function calls
# INPUT:    Tree element (usually root)
# OUTPUT:   None
def postConversionCleanup(root: ET.Element):
    removeall(root, ".//routes")
    removeall(root, ".//paths")
    removeall(root, ".//vertices")



# ================ JENIEVA'S FUNCTIONS ================

# PURPOSE:  Creates a list of blanks or "turnback" by looping through each vertex in each itinerary that will be outputted to the turnback check output file
# INPUT:    csv input as dataframe
# OUTPUT:   turnback list
def create_turnbacks_list(df_in):
    vertexID_documentName_list = []
    neighbourID_documentName_list = []
    turnbacks = []
    turnback_found = False

    for row in range(len(df_in)):

        # this is just to output an update to the user so they know that the code is still running
        if row == round(len(df_in)/4):
            print(f"25% complete...")
        elif row == round(len(df_in)/2):
            print(f"50% complete...")
        elif row == round((len(df_in)/4)*3):
            print(f"75% complete...")
        elif row == round(len(df_in)):
            print(f"100% complete...")

        # within each itinerary block, two arrays are made for each row, which contain the vertex ID/corridor and neighbour vertex ID/corridor.
        # the arrays are each added to a seperate list and once the for loop has reached the end of the itinerary, the lists are compared to see if any of the neighbour vertex ID's are listed in the vertex ID list.
        # it is important to check the corridor as well because there are duplicate vertex ID's but the real neighbour vertex ID for a given vertex will have the same corridor
        if df_in.loc[row, 'itinerary'] != '':
            vertexID_array = [df_in.loc[row, "documentName"], df_in.loc[row, "vertexID"]]
            neighbourID_array = [df_in.loc[row, "documentName"], df_in.loc[row, "neighbourID"]]
            vertexID_documentName_list.append(vertexID_array)
            neighbourID_documentName_list.append(neighbourID_array)
        elif df_in.loc[row, 'itinerary'] == '':
            for neighbour in neighbourID_documentName_list:
                if neighbour in vertexID_documentName_list[neighbourID_documentName_list.index(neighbour):]:
                    turnback_found = True
                    break
            if turnback_found == True:
                turnbacks.append('Turnback')
            else:
                turnbacks.append('')

            vertexID_documentName_list = []
            neighbourID_documentName_list = []
            turnback_found = False

    return turnbacks

# PURPOSE:  Creates a list of all of the itineraries that will be outputted to the turnback check output file
# INPUT:    csv input as dataframe
# OUTPUT:   itineraries list
def create_itineraries_list(df_in):
    itineraries = []
    # this basically just loops through all of the itineraries in the csv file and prints each one out once rather than how it is shown in the csv file
    for i in range(len(df_in['itinerary'])):
        if i == len(df_in['itinerary']):
            itineraries.append(df_in.loc[i,'itinerary'])
        else:
            if df_in.loc[i,'itinerary'] != '':
                if df_in.loc[i,'itinerary'] != df_in.loc[i+1,'itinerary']:
                    itineraries.append(df_in.loc[i,'itinerary'])

    return itineraries

# PURPOSE:  Creates a list of all of the possible courseIDs that each itinerary (with a turnback) could corrispond to in the timetable based on the course.xml file.
#           This list is outputted to the turnback check output file
# INPUT:    course.xml input as dataframe, list of turnbacks, list of itineraries
# OUTPUT:   courseID's list
def create_courseID_list(df_course_xml, itineraries, turnback, x):
    courseID = []
    # this loops through each itinerary in the list of itineraries, identifies if it is a turnback (by checking the turnback list),
    # and if it is, finds all of the instances of that itinerary within the course.xml df and returns the possible courseIDs.
    for i in range(len(itineraries)):
        if turnback[i] == 'Turnback':
            if itineraries[i] != '':
                for j in range(len(df_course_xml['Itinerary'])):
                    if df_course_xml.loc[j, 'Itinerary'] == itineraries[i]:
                        if df_course_xml.loc[j, 'Itinerary'] != df_course_xml.loc[j+1, 'Itinerary']:
                            courseID.append(df_course_xml.loc[j, 'CourseID'])
                            x += 1
                            break
                        elif df_course_xml.loc[j, 'Itinerary'] == df_course_xml.loc[j+1, 'Itinerary']:
                            courseID.append(df_course_xml.loc[j, 'CourseID'])
                            for l in range(j+1,len(df_course_xml['Itinerary'])):
                                if df_course_xml.loc[j, 'Itinerary'] == df_course_xml.loc[l, 'Itinerary']:
                                    courseID[x] = str(courseID[x]) + ', ' + str(df_course_xml.loc[l, 'CourseID'])
                            x += 1
                            break
                    elif j == (len(df_course_xml['Itinerary'])-1):
                        courseID.append('Itinerary not listed in course.xml')
                        x += 1
        else:
            courseID.append('')
            x += 1     
    return courseID


# PURPOSE:  Output the itinerary list, turnback list, and courseID list
# INPUT:    output dataframe, itinerary list, turnback list, courseID list
# OUTPUT:   None
def df_final_output(df_final, itineraries, turnback, courseID):
    df_final['Itinerary'] = itineraries
    
    for i in range(len(turnback)):
        # output the routes list to the routes column of output file
        df_final.loc[i,'Turnback'] = turnback[i]
    
    for i in range(len(courseID)):
        df_final.loc[i, 'CourseID'] = courseID[i]


# ================ MAIN FUNCTION ================
 
# PURPOSE:  Run all code within main function to improve runtime
# INPUT:    None
# OUTPUT:   None
def main():

    # ================ MICHAEL'S MAIN SECTION ================
    # ================ USER INPUTS & OUTPUTS ================
    os.chdir(os.path.dirname(__file__)) #set working directory to the same as the script. Python is supposed to set this by default, idk why it isn't. Removing this line
    inputFile = gui.fileopenbox(msg="Select the itinerary.xml", filetypes=['*.xml']) #Get input file location
    input = open(inputFile, 'r')

    # ================ XML conversion ================
    tree = ET.parse(input) #parse input xml file, assign handle "tree"
    root = tree.getroot()

    #Pre-conversion data cleanup
    preConversionCleanup(root)

    #Element tree conversion: 
    for branch in root:
        if branch.tag == "itineraries":
            print("\nConverting .xml file into .csv file")
            print("Moving paths. Elapsed time: %s seconds" % (time.time()-start_time)) 

            # Replace <itineraries> path nodes with <paths> path nodes
            for itineraryNode in branch:
                for pathNode in list(itineraryNode):
                    copiedPath = searchNode(root, pathNode)
                    itineraryNode.append(copiedPath)
                    itineraryNode.remove(pathNode)
            print("Moving routes. Elapsed time: %s seconds" % (time.time()-start_time))

            # Replace <itineraries> route nodes with <routes> route nodes     
            for itineraryNode in branch:
                for pathNode in itineraryNode:
                    for routeNode in list(pathNode):
                        copiedRoute = searchNode(root, routeNode)
                        pathNode.append(copiedRoute)
                        pathNode.remove(routeNode)
            print("Moving vertices. Elapsed time: %s seconds" % (time.time()-start_time))

            print("\nFinalizing xml reformatting...")
            print("This may take a few minutes, do not close program")
            # Replace <itineraries> vertex nodes with <vertices> vertex nodes
            for itineraryNode in branch:
                for pathNode in itineraryNode:
                    for routeNode in pathNode:
                        for vertexNode in list(routeNode):
                            
                            copiedVertex = searchNode(root, vertexNode)
                            routeNode.append(copiedVertex)
                            routeNode.remove(vertexNode)
                    
    # Clean output
    postConversionCleanup(root)

    # Redo tabbing in xml for readability
    ET.indent(tree, "\t")

# ================ WRITE TO .csv ================
    #Write element tree into rows for dataframe
    print("Writing output. Elapsed time: %s seconds" % (time.time()-start_time)) 
    for branch in root:
        for itineraryNode in branch:
            for path in itineraryNode:
                for route in path:
                    for vertex in route:
                        vertexName = vertex.get("name")
                        documentname = vertex.get("documentname")
                        id = vertex.get("id")
                        neighbourid = vertex.get("neighbourid")

                        rows.append({"itinerary": itineraryNode.get("name"), #Build output rows
                                     "path": path.get("name"),
                                     "route": route.get("name"),
                                     "documentName": documentname,
                                     "vertexName": vertexName,
                                     "vertexID": id,
                                     "neighbourID": neighbourid})
            rows.append({"itinerary": "", #Build blank row after each itinerary
                         "path": "",
                         "route": "",
                         "documentName": "",
                         "vertexName": "",
                         "vertexID": "",
                         "neighbourID": ""})
                        
    # Build dataframe for csv write
    df = pd.DataFrame(rows, columns=cols)
    

    #tree.write('XML_To_CSV_Output.xml') #Un-comment this line for an xml output
    df.to_csv("XML_To_CSV_Output.csv", index = False)


    # ================ JENIEVA'S MAIN SECTION ================
    final_time = time.time()

    # read csv file
    df_in = pd.read_csv('XML_To_CSV_Output.csv', dtype = str)
    df_in.drop(df_in.columns[4], axis=1, inplace=True)

    # to deal with empty rows being shown in df as na, a true/false df copy of the input df is made to filter out all na's to be blanks
    df_true_false = df_in.notna()

    # replacing all false values in the true/false df with blanks in the input df
    for i in range(len(df_true_false['vertexID'])):
        if df_true_false.loc[i, 'vertexID'] == False:
            df_in.loc[i, 'vertexID'] = ''

    for i in range(len(df_true_false['itinerary'])):
        if df_true_false.loc[i, 'itinerary'] == False:
            df_in.loc[i, 'itinerary'] = ''

    # read course xml file
    df_course_xml = pd.read_csv('course_xml.csv')

    df_course_xml.drop(df_course_xml.columns[1:11], axis=1, inplace=True)
    df_course_xml.drop(df_course_xml.columns[2], axis=1, inplace=True)

    # create final df
    df_final = pd.DataFrame(columns=['Itinerary', 'Turnback', 'CourseID'])

    # running each function (to create lists that are outputted in final df)
    print("\nLooking for turnbacks...")
    turnbacks = create_turnbacks_list(df_in)

    time_passed = time.time()-final_time
    minutes = math.trunc(time_passed/60)
    seconds = time_passed - (math.trunc(time_passed/60))*60
    print('All turnbacks have been found. It has been', minutes, 'minutes and', seconds, 'seconds. \n')

    print('Preparing output file...')
    itineraries = create_itineraries_list(df_in)
    courseIDs = create_courseID_list(df_course_xml, itineraries, turnbacks, 0)
    df_final_output(df_final, itineraries, turnbacks, courseIDs)
    df_final.to_excel('Turnback_Check_Output.xlsx', index = False)
    print('Final output complete \n')


# ================ MAIN ================
if __name__ == "__main__":

    start_time = time.time() #store start time
    
    main()

    time_passed = time.time()-start_time
    minutes = math.trunc(time_passed/60)
    seconds = time_passed - (math.trunc(time_passed/60))*60
    print("Process finished ---", minutes, "minutes and", round(seconds, 2), "seconds ---") #Print end time


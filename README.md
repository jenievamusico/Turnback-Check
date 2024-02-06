# This script converts InfrastructureData.xml files exported from OpenTrack and converts them to .csv files.
# It then scans the .csv file and identifies any itineraries containing trains that turnback within a trip.
# The script then references the course.xml file outputted from OpenTrack to find the courseID of each itinerary.
# Finally, the script outputs the .csv file as well as a file containing every itinerary, whether it contains a turnback, and the possible train courseID's if a turnback is detected.

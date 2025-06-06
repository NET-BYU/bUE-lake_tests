import sys
import time
from datetime import datetime
from loguru import logger


import survey

from base_station_main import Base_Station_Main

def send_test(base_station, bue_indexes, file_name, start_time, parameters):
    bues = [base_station.connected_bues[index] for index in bue_indexes]
    for bue in bues:
        base_station.testing_bues.append(bue)
        base_station.ota.send_ota_message(bue, f"TEST-{file_name}-{start_time}-{parameters}")

# This function handles the console input for sending commands to bUEs      
def user_input_handler(base_station):
    
    ## TODO: GPS timing needs to be included

    COMMANDS = ("TEST", "DISTANCE", "DISCONNECT", "CANCEL", "LIST", "EXIT")

    FILES = ("RX", "TX", "helloworld", "gpstest", "gpstest2")

    while not base_station.EXIT: ## TODO: Make sure that connected_bues_tests are taken out
        try:
            index = survey.routines.select('Pick a command: ', options = COMMANDS)

            if(index != 5 and len(base_station.connected_bues) == 0):
                print("Currently not connected to any bUEs")
                continue

            if index == 0: #TEST
                connected_bues = tuple(str(x) for x in base_station.connected_bues)
                if(len(connected_bues) == 0):
                    print("Currently not connected to any bUEs")
                
                bues_indexes = survey.routines.basket('What bUEs will be running tests?', options = connected_bues)
                ## TODO: Should there be a check to see if a bUE is currently being tested or trust the user to handle this themselves?

                file_index = survey.routines.select('What file would you like to run? ', options = FILES)
                file_name = FILES[file_index]

                start_time = survey.routines.datetime('When would you like to run the test? ',  attrs = ('hour', 'minute', 'second')).time()
                ## TODO: It would be nice if these parameters setup to conincide with the script being run

                parameters = survey.routines.input('Enter parameters separated by a space:\n')

                send_test(base_station, bues_indexes, file_name, start_time, parameters)


            elif index == 1: #DISTANCE
                connected_bues = tuple(str(x) for x in base_station.connected_bues)
                if(len(connected_bues) == 0):
                    print("Currently not connected to any bUEs")

                indexes = survey.routines.basket('Select two bUEs',
                                                options = connected_bues)
                
                ## TODO: Need to implement the rest of this once I fixed the coordinates 

            if index == 2: # DISCONNECT
                connected_bues = tuple(str(x) for x in base_station.connected_bues)
                if(len(connected_bues) == 0):
                    print("Currently not connected to any bUEs")

                indexes = survey.routines.basket('What bUEs do you want to disconnect from?',
                                                options = connected_bues)
                
                print("\n")
                for i in indexes:
                    bue = base_station.connected_bues[i]
                    print(f"Disconnected from {base_station.connected_bues[i]}")
                    base_station.connected_bues.remove(bue)
                    if bue in base_station.bue_coordinates.keys():
                        del base_station.bue_coordinates[bue]
                print("\n")
            
            elif index == 3: # CANCEL
                testing_bues = tuple(str(x) for x in base_station.testing_bues)
                if(len(testing_bues) == 0):
                    print("No bUEs are currently running any tests")

                indexes = survey.routines.basket('What bUE tests do you want to cancel?',
                                                options = testing_bues)
                
                print("\n")
                ## TODO: Send a CANC to each of these bUEs
                for i in indexes:
                    bue = base_station.testing_bues[i]
                    print(f"Ending test for {base_station.testing_bues[i]}")
                    base_station.ota.send_ota_message(bue, "CANC")
                print("\n")

            elif index == 4: # LIST
                print("\n")
                connected_bues = " ".join(str(bue) for bue in base_station.connected_bues)
                print(f"Currently connected to {connected_bues}\n\n")
                logger.info(f"Currently connected to {connected_bues}")
            
            elif index == 5: # EXIT
                base_station.EXIT = True
                base_station.__del__()
                # if 'user_input_thread' in locals() and user_input_thread.is_alive():
                #     user_input_thread.join(timeout=2.0)
                sys.exit(0)

        except KeyboardInterrupt:
            print("\n[Escape] Cancelled input. Returning to command prompt.\n")
            continue 


        except Exception as e:
            logger.error(f"[User Input] Error {e}")
            print(e)


if __name__ == "__main__":
    start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    logger.info(f"This marks the start of the base station service at {start_time}")

    try:
        base_station = Base_Station_Main(yaml_str="config_base.yaml")

        # user_input_thread = threading.Thread(target=user_input_handler, args=(base_station,))
        # user_input_thread.start()

        base_station.tick_enabled = True

        user_input_handler(base_station)

        while not base_station.EXIT:
            time.sleep(0.2)

    except KeyboardInterrupt:
        logger.info("Exiting the Base Station service")
        if base_station is not None:
            base_station.EXIT = True
            time.sleep(0.5)
            base_station.__del__()
        # if 'user_input_thread' in locals() and user_input_thread.is_alive():
        #     user_input_thread.join(timeout=2.0)
        sys.exit(0)
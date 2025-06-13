from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
import survey
import sys

class KeyLogger():
    def user_input_handler():
    
    ## TODO: GPS timing needs to be included

        COMMANDS = ("TEST", "DISTANCE", "DISCONNECT", "CANCEL", "LIST", "EXIT")

        FILES = ("RX", "TX", "helloworld", "gpstest", "gpstest2")

        while True: ## TODO: Make sure that connected_bues_tests are taken out
            try:
                index = survey.routines.select('Pick a command: ', options = COMMANDS)
                
                if index == 5: # EXIT
                    # if 'user_input_thread' in locals() and user_input_thread.is_alive():
                    #     user_input_thread.join(timeout=2.0)
                    sys.exit(0)

            except KeyboardInterrupt:
                print("\n[Escape] Cancelled input. Returning to command prompt.\n")
                continue 


            except Exception as e:
                print(e)


class UtilityContainersExample(App):
    CSS_PATH = "utility_containers.tcss"

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Static("One"),
                Static("Two"),
                classes="column",
            ),
            Vertical(
                Static("Three"),
                Static("Four"),
                classes="column",
            ),
        )
        yield KeyLogger()


if __name__ == "__main__":
    app = UtilityContainersExample()
    app.run()
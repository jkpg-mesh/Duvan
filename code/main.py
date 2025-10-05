"""
Duvan Beacon - A Meshtastic Utility

License: MIT
Repository: https://github.com/jkpg-mesh/mesh-repeater

Description:
This application enables a Meshtastic united connected to the processing unit
to serve as a 'beacon' that can serve the community base.  It was written 
with the ability to add additional modules or functions. 

Run this on a PC or Raspberry Pi connected to a Meshtastic device over USB.
"""

from datetime import datetime
import json, logging, os, time
import meshtastic.serial_interface
from pubsub import pub
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

ACTIVE_DIR = os.path.dirname(os.path.abspath(__file__))

def clear_screen():
    """
    Clear the console screen.
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def init_startup_screen():
    """
    Initialize and display the startup screen with ASCII art.
    """
    global console

    console = Console(force_terminal=True)
    clear_screen()

    # Your provided ASCII art
    duvan_ascii = """
    ______                            
    |  _  \                           
    | | | |_   ___   ____ _ _ __      
    | | | | | | \ \ / / _` | '_ \     
    | |/ /| |_| |\ V / (_| | | | |    
    |___/  \__,_| \_/ \__,_|_| |_|                              
    ______                            
    | ___ \                           
    | |_/ / ___  __ _  ___ ___  _ __  
    | ___ \/ _ \/ _` |/ __/ _ \| '_ \ 
    | |_/ /  __/ (_| | (_| (_) | | | |
    \____/ \___|\__,_|\___\___/|_| |_|                                                                 
    """

    # Apply rich styling to the ASCII art
    # You can customize the color (e.g., "bold blue", "green", "yellow on black")
    colored_ascii = Text(duvan_ascii, style="bold bright_cyan")

    # Display the ASCII art in a Panel for a structured look
    console.print(Panel(colored_ascii, box=box.ROUNDED, title="[bold magenta]System Boot Sequence[/bold magenta]",
                         border_style="green", expand=False))

def numToHex(node_num):
    """
    Convert a node number to a hexadecimal string prefixed with '!'.
    :param node_num: The node number to convert.
    :return: A string representing the node number in hexadecimal format.
    """
    return '!' + hex(node_num)[2:]

def init_logging():
    """
    Initialize logging configuration.
    """
    global log_filename
    log_filename = f"logs/system_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_filename = os.path.join(ACTIVE_DIR, log_filename)
    logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Initialized logging...")
    console.print(f"[bold green]✔[/bold green]  Initialized logging...")

def loadConfig(path='config/config.json'):
    """
    Load configuration from a JSON file.
    :param path: Path to the configuration file.
    :return: Configuration dictionary or None if loading fails."""
    
    try:
        with open(os.path.join(ACTIVE_DIR, path), 'r',encoding="utf-8") as f:
            config = json.load(f)
            return config
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        console.print(f"[bold red]❌[/bold red]  Initialized configuration...")
        return None

def loadCommands(path='config/commands.json'):
    """
    Load commands from a JSON file.
    :param path: Path to the commands file.
    :return: Commands dictionary or None if loading fails."""
    try:
        with open(os.path.join(ACTIVE_DIR, path), 'r',encoding="utf-8") as f:
            commands = json.load(f)
            return commands
    except Exception as e:
        logging.error(f"Failed to load commands: {e}")
        console.print(f"[bold red]❌[/bold red]  Initialized commands...")
        return None

def saveConfig(config, path='config/config.json'):
    """
    Save configuration to a JSON file.
    :param config: Configuration dictionary to save.
    :param path: Path to the configuration file.
    """
    try:
        with open(os.path.join(ACTIVE_DIR, path), 'w',encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            logging.info("Configuration saved successfully...")
            console.print(f"[bold green]✔[/bold green]  Configuration saved successfully...")
    except Exception as e:
        logging.error(f"Failed to save config: {e}")
        console.print(f"[bold red]❌[/bold red]  Failed to save configuration...") 

def init_config():
    """
    Initialize configuration by loading from file.
    """
    global config
    config = loadConfig()

    if config == None:
        pass
    else:
        logging.info("Initialized configuration...")
        console.print(f"[bold green]✔[/bold green]  Initialized configuration...")

def init_commands():
    """
    Initialize commands by loading from file.
    """
    global commands
    commands = loadCommands()

    if commands == None:
        pass
    else:
        logging.info("Initialized commands...")
        console.print(f"[bold green]✔[/bold green]  Initialized commands...")

def init_modules():
    """
    Initialize and start all additional modules as separate threads.

    As example:
    # Start the broadcast thread
    broadcaster = broadcast.broadcast(interface=interface, 
                                      config=config,
                                      shared_data=shared_data)
    broadcast_thread = threading.Thread(target=broadcaster.run, 
                                        daemon=True)
    broadcast_thread.start()
    """
    # Declare valiables that must be accessible in other modules
    # global 

    logging.info("Initialized Modules...")
    console.print(f"[bold green]✔[/bold green]  Initialized Modules...")

def command_handler(packet):
    """
    Handle commands received in text messages.
    :param packet: The received packet containing the command.
    :return: Response message or None if no response is needed.
    """
    message = packet['decoded']['text']
    # extract rssi and snr from packet and formats return message
    rssi = packet.get('rxRssi')
    snr = packet.get('rxSnr')
    if rssi is not None:
        rssi_msg = f"{round(rssi, 2)} dBm"
    else:
        rssi_msg = "--.-- dBm"
    if snr is not None:
        snr_msg = f"{round(snr, 2)} dB"
    else:
        snr_msg = "--.-- dB"

    # Split by whitespace
    parts = message.strip().split()
    if not parts:
        return "Empty command."

    received_cmd = parts[0]
    args = parts[1:]

    for available_cmd in commands["commands"]:
        if received_cmd == available_cmd["command"]:
            try:
                msg = available_cmd["response"].format(rssi_msg=rssi_msg, snr_msg=snr_msg)
            except KeyError:
                msg = available_cmd["response"]
            return msg
    return None

def onReceive(packet, interface):
    """
    Handle incoming packets from the Meshtastic device.
    :param packet: The received packet.
    :param interface: The Meshtastic interface instance.
    """
    try:
        match packet['decoded']['portnum']:
            case "TELEMETRY_APP":
                # Handle telemetry packets here if needed
                pass
            case "TEXT_MESSAGE_APP":
                fromId = numToHex(packet['from'])
                body = packet['decoded']['text']
                msg = command_handler(packet)
                if msg != None:
                    sendMessage(interface=interface, toID=fromId, message=msg)
            case "POSITION_APP":
                # Handle position packets here if needed
                pass
            case "NODEINFO_APP":
                # Handle node info packets here if needed
                pass
    except Exception as e:
        logging.warning(f"Error parsing packet: {e}")

def onConnection(interface:meshtastic.serial_interface.SerialInterface, topic=pub.AUTO_TOPIC):
    """
    Handle actions to take when the connection to the Meshtastic device is established.
    :param interface: The Meshtastic interface instance.
    :param topic: The pubsub topic (default is AUTO_TOPIC).
    """
    logging.info("Connected to Meshtastic device.")
    myUser = interface.getMyUser()
    logging.info(f"Unit Long Name: {myUser['longName']}")
    logging.info("Unit Short Name: "+myUser['shortName'])
    logging.info(f"Unit Id: {myUser['id']}")
    logging.info(f"Model: {myUser['hwModel']}")

def onConnectionLost(interface:meshtastic.serial_interface.SerialInterface):
    """
    Handle actions to take when the connection to the Meshtastic device is lost.
    :param interface: The Meshtastic interface instance.
    """
    logging.info("Connection lost")

def sendMessage(interface:meshtastic.serial_interface.SerialInterface, toID, message):
    """
    Send a text message to a specific node.
    :param interface: The Meshtastic interface instance.
    :param toID: The destination node ID.
    :param message: The message to send.
    """
    logging.debug(f"Sending message to {toID}: {message}")
    interface.sendText(text=message, destinationId=toID)

def init_meshunit():
    """
    Initialize the Meshtastic interface and set up event subscriptions.
    """
    global interface, MeshError
    interface = None # Initialize interface to None outside the try block

    # Subscribe to Meshtastic events
    time.sleep(0.5)
    pub.subscribe(onReceive, "meshtastic.receive")
    console.print(f"[bold green]✔[/bold green]  Initialized onReceive...")
    time.sleep(0.5)
    pub.subscribe(onConnection, "meshtastic.connection.established")
    console.print(f"[bold green]✔[/bold green]  Initialized onConnection...")
    time.sleep(0.5)
    pub.subscribe(onConnectionLost, "meshtastic.connection.lost")
    console.print(f"[bold green]✔[/bold green]  Initialized onConnectionLost...")
    
    try:
        # Start the Meshtastic serial interface
        # This might print "No Serial Meshtastic device detected..." if none is found
        interface = meshtastic.serial_interface.SerialInterface()
        logging.info("Meshtastic interface attempting connection...")

        # Give the interface a moment to connect or fail to connect
        time.sleep(3) # A short delay to allow connection attempts

        #Used to check if connected to serial device
        myLongName = interface.getLongName()
        console.print(f"[bold green]✔[/bold green]  Initialized Meshtastic interface...")
        time.sleep(0.5)
        logging.info("Meshtastic function started...")
        console.print(f"[bold green]✔[/bold green]  Meshtastic function started...")

    except Exception as e:
        # Catch any other unexpected errors during the process
        logging.error(f"An unexpected error occurred: {e}")
        console.print(f"[bold red]❌[/bold red]  Meshtastic function started...")
        MeshError = str(e)

def main():
    """
    Main function to initialize and run the repeater application.
    """

    init_startup_screen()
    init_logging()
    init_config()
    init_commands()
    init_meshunit()
    init_modules()
    
    logging.info("Initialized Repeater ...")
    console.print(f"[bold green]✔[/bold green]  Initialized Beacon ...")

    while True:
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt caught. Exiting...")
        console.print(f"[bold green]✔[/bold green]  KeyboardInterrupt caught. Exiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # This ensures the connection is closed cleanly whether there was an error or not
        saveConfig(config)
        console.print(f"[bold green]✔[/bold green]  Saving configuration...")
        logging.info("Closing the Meshtastic interface...")
        console.print(f"[bold green]✔[/bold green]  Closing the Meshtastic interface...")
        interface.close()
        logging.info("Meshtastic interface closed...")
        console.print(f"[bold green]✔[/bold green]  Meshtastic interface closed...")
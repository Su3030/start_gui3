#############################################everything is good except for the right part it needs to be a little bit upward,message not good 29/9/2024_12:20PM
import random
import streamlit as st
import pandas as pd
from pyftdi.ftdi import Ftdi
from pyftdi.i2c import I2cController, I2cNackError
from io import BytesIO
import xlsxwriter
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
# Set Streamlit to always run in wide mode
st.set_page_config(layout="wide")



# Add logo image with CSS margin adjustment to move it up
logo_path = r"C:\Users\LOQ3\Downloads\logo.png"
st.markdown(
    f"""
    <style>
    .logo-container {{
        margin-bottom: -20px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)
st.image(logo_path, width=480)



# Create an Ftdi object
ftdi = Ftdi()

# Open the first FT232H device
ftdi.open_bitbang_from_url('ftdi://ftdi:232h/1')

st.markdown("""
    <style>
    /* Custom wrapper for the I2C frequency input box */
    .custom-number-input {
        position: relative; /* Ensure we can move the entire box */
        width: 250px; /* Adjust width */
        margin-left: -100px;  /* Move the entire box to the right */
        margin-top: -50px;  /* Move the entire box upwards */
    }
    </style>
    """, unsafe_allow_html=True)

# Create an I2C controller instance and configure it
controller = I2cController()
controller.configure(url='ftdi://ftdi:232h/1')
# Wrap the input box in a div with a custom class
st.markdown('<div class="custom-number-input">', unsafe_allow_html=True)
frequency = st.number_input('Set I2C Frequency (Hz):', min_value=1, max_value=3400000, value=100000, step=1)
st.markdown('</div>', unsafe_allow_html=True)

#frequency = st.number_input('Set I2C Frequency (Hz):', min_value=1, max_value=1000000, value=100000, step=1)
controller.configure(url='ftdi://ftdi:232h/1', frequency=frequency)

# Constants
BINARY_NUMBERS = [format(i, '08b') for i in range(256)]
HEX_NUMBERS = [format(i, '02X') for i in range(256)]
DECIMAL_NUMBERS = [str(i) for i in range(256)]




# Initialize session state for logs if not already present
if 'log_list' not in st.session_state:
    st.session_state.log_list = []

def format_as_hex (value):
    """Helper function to format a value as hexadecimal."""
    return format(value, '02X')






def read_register_with_repeated_start(i2c_address, register_address, num_bytes=1):
    """Function to read data from a register."""
    try:
        register_address_int = int(register_address, 16)
        port = controller.get_port(i2c_address)
        port.write([register_address_int], relax=False)
        read_data = port.read(num_bytes)
        hex_value = read_data.hex().upper()
        st.session_state.log_list.append({
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'address': f'{i2c_address:02X}',
            'register': f'{register_address}',
            'value': hex_value,
            'operation': 'Read'
        })
        return read_data
    except ValueError:
        st.error("Invalid register address. Please provide a hexadecimal value.")
    except I2cNackError as e:
        st.error(f"I2C NACK error: {e}")
        st.session_state.log_list.append({
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'address': f'{i2c_address:02X}',
            'register': f'{register_address}',
            'value': 'N/A',
            'operation': 'I2C is not responding'
        })
        return None


def test_write_registers(i2c_address, registers):
    """Function to test writing to registers."""
    results = {f'Register {register:02X}': ['' for _ in HEX_NUMBERS] for register in registers}
    results['Value'] = HEX_NUMBERS
    placeholder = st.empty()  # Use placeholder for the main content, not the sidebar
    for register in registers:
        for i, hex_value in enumerate(HEX_NUMBERS):
            try:
                data_to_write = int(hex_value, 16)
                port = controller.get_port(i2c_address)
                port.write([register, data_to_write])
                results[f'Register {register:02X}'][i] = 'Success'
                st.session_state.log_list.append({
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'address': f'{i2c_address:02X}',
                    'register': f'{register:02X}',
                    'value': hex_value,
                    'operation': 'Write'
                })
            except I2cNackError:
                results[f'Register {register:02X}'][i] = 'NACK from slave'
                st.session_state.log_list.append({
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'address': f'{i2c_address:02X}',
                    'register': f'{register:02X}',
                    'value': 'N/A',
                    'operation': 'I2C is not responding'
                })
        write_results_df = pd.DataFrame(results)
        placeholder.dataframe(write_results_df, height=400, width=1000)
    return results

def test_read_registers(i2c_address, registers):
    """Function to test reading from registers."""
    results = {f'Register {register:02X}': ['' for _ in HEX_NUMBERS] for register in registers}
    results['Value'] = HEX_NUMBERS
    placeholder = st.empty()
    for register in registers:
        for i, hex_value in enumerate(HEX_NUMBERS):
            try:
                data_to_write = int(hex_value, 16)
                port = controller.get_port(i2c_address)
                port.write([register, data_to_write])
                port.write([register], relax=False)
                read_data = port.read(1)
                read_value = int.from_bytes(read_data, byteorder='big')
                formatted_read_value = format_as_hex(read_value)
                if formatted_read_value == hex_value:
                    results[f'Register {register:02X}'][i] = 'Success-Match'
                else:
                    results[f'Register {register:02X}'][i] = 'Mismatch'
                st.session_state.log_list.append({
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'address': f'{i2c_address:02X}',
                    'register': f'{register:02X}',
                    'value': formatted_read_value,
                    'operation': 'Read'
                })
            except I2cNackError:
                results[f'Register {register:02X}'][i] = 'NACK Error'
                st.session_state.log_list.append({
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'address': f'{i2c_address:02X}',
                    'register': f'{register:02X}',
                    'value': 'N/A',
                    'operation': 'I2C is not responding'
                })
        read_results_df = pd.DataFrame(results)
        placeholder.dataframe(read_results_df, height=400, width=1000)
    return results

def save_to_excel(dataframe, file_name):
    """Function to save dataframe to Excel."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Results')
    buffer.seek(0)
    return buffer

def test_random_operations_multiple_addresses(i2c_addresses, registers):
    """Function to test random read/write operations on multiple addresses."""
    results = []
    for _ in range(10000):  # 2000 iterations
        i2c_address = random.choice(i2c_addresses)
        register = random.choice(registers)
        operation = random.choice(['write', 'read'])
        hex_value = random.choice(HEX_NUMBERS)
        try:
            port = controller.get_port(i2c_address)
            if operation == 'write':
                data_to_write = int(hex_value, 16)
                port.write([register, data_to_write])
                results.append({
                    'I2C Address': f'{i2c_address:02X}',
                    'Register': f'{register:02X}',
                    'Operation': 'Write',
                    'Value': hex_value,
                    'Status': 'Success'
                })
                st.session_state.log_list.append({
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'register': f'{register:02X}',
                    'value': hex_value,
                    'operation': 'Write',
                    'address': f'{i2c_address:02X}'
                })
            else:
                port.write([register], relax=False)
                read_data = port.read(1)
                read_value = int.from_bytes(read_data, byteorder='big')
                formatted_read_value = format_as_hex(read_value)
                results.append({
                    'I2C Address': f'{i2c_address:02X}',
                    'Register': f'{register:02X}',
                    'Operation': 'Read',
                    'Value': formatted_read_value,
                    'Status': 'Success'
                })
                st.session_state.log_list.append({
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'register': f'{register:02X}',
                    'value': formatted_read_value,
                    'operation': 'Read',
                    'address': f'{i2c_address:02X}'
                })
        except I2cNackError:
            results.append({
                'I2C Address': f'{i2c_address:02X}',
                'Register': f'{register:02X}',
                'Operation': operation.capitalize(),
                'Value': hex_value,
                'Status': 'NACK Error'
            })
            st.session_state.log_list.append({
                'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'register': f'{register:02X}',
                'value': hex_value,
                'operation': 'NACK Error',
                'address': f'{i2c_address:02X}'
            })
    
    return results





#########################################################################################
#WRITE OPERATION
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

# Define column widths: left is wider, right is smaller
col1, col2 = st.columns([3, 1])


def plot_i2c_write_waveform(i2c_address, register, data,operation='write'):
    """Generate and plot the I2C/write waveform for a write operation with negative-edge triggering, using colors for each segment."""
    fig, ax = plt.subplots(figsize=(12, 5))

    
    # Initialize timing and signals for SCL and SDA
    timing = []
    scl = []  # SCL line
    sda = []  # SDA line
    colors = []  # Store color for each segment

    def append_timing_steps(steps, scl_state, sda_state, color):
        """Helper function to append timing steps to the waveform."""
        timing.extend([len(timing) + i for i in range(steps)])
        scl.extend([scl_state] * steps)
        sda.extend([sda_state] * steps)
        colors.extend([color] * steps)
        
         #3// is how short or long the signal


    # START condition: SDA goes low while SCL is high (Red)
    append_timing_steps(3, 1, 1, 'red')  # Idle state (SDA = SCL = 1)
    append_timing_steps(3, 1, 0, 'red')  # Start condition (SDA falls)

    # Slave Address (Blue) + Write bit (Cyan)
    address_bits = [int(bit) for bit in f'{i2c_address:07b}']  # 7-bit address
    for bit in address_bits:
        append_timing_steps(3, 1, bit, 'blue')  # SCL high, set SDA to bit (setup data when SCL is high)
        append_timing_steps(3, 0, bit, 'blue')  # SCL low, hold SDA (sample data on falling edge)

    # Write bit (0) - Cyan
    append_timing_steps(3, 1, 0, 'purple')  # SCL high, set SDA to write bit (0)
    append_timing_steps(3, 0, 0, 'purple')  # SCL low, hold SDA (sample write bit)

    # ACK from slave (Green)
    append_timing_steps(3, 1, 0, 'green')  # SCL high, prepare for ACK
    append_timing_steps(3, 0, 0, 'green')  # SCL low, ACK is low (sample ACK on falling edge)

    # Register Address (Orange)
    register_bits = [int(bit) for bit in f'{register:08b}']
    for bit in register_bits:
        append_timing_steps(3, 1, bit, 'orange')  # SCL high, set SDA to bit (setup data)
        append_timing_steps(3, 0, bit, 'orange')  # SCL low, hold SDA (sample data)

    # ACK from slave (Green)
    append_timing_steps(3, 1, 0, 'green')  # SCL high, prepare for ACK
    append_timing_steps(3, 0, 0, 'green')  # SCL low, ACK is low (sample ACK)

    # Data Byte (Purple)
    for byte in data:
        data_bits = [int(bit) for bit in f'{byte:08b}']
        for bit in data_bits:
            append_timing_steps(3, 1, bit, 'brown')  # SCL high, set SDA to bit (setup data)
            append_timing_steps(3, 0, bit, 'brown')  # SCL low, hold SDA (sample data)

    # NACK from master (Yellow)
    append_timing_steps(3, 1, 1, 'green')  # SCL high, prepare for NACK
    append_timing_steps(3, 0, 1, 'green')  # SCL low, NACK is high (sample NACK)

    # STOP condition: SDA goes high while SCL is high (Red)
    append_timing_steps(3, 0, 0, 'red')  # SCL low, prepare for stop
    append_timing_steps(3, 1, 1, 'red')  # Stop condition (SDA rises)

    # Generate timing values for the x-axis
    timing = np.arange(len(scl))

    # Offset SDA signal for separation
    sda_offset = 1.5
    sda = [x + sda_offset for x in sda]

    # Plotting the SCL and SDA signals with colors for each segment
    for i in range(len(timing) - 1):
        ax.step(timing[i:i+2], scl[i:i+2], color=colors[i], lw=2)
        ax.step(timing[i:i+2], sda[i:i+2], color=colors[i], lw=2)

   
 

    # Add labels and grid
    ax.set_title("I2C Write Operation ")
    ax.set_xlabel("Time (us)")
    ax.set_ylabel("Signal Logical Level")
     #the Y-aix is from -0.5 t0 3.5
    ax.set_ylim(-1, sda_offset + 2.1)
    ax.grid(True)

  
 

# Add labels for SCL and SDA lines
    ax.text(0, 1, 'SCL', color='black', ha='right', va='center', fontsize=8)
    ax.text(0, sda_offset + 1, 'SDA', color='black', ha='right', va='center', fontsize=8)


# Draw boxes for each I2C segment (covering the whole signal height)
    segments = [
        (-3, 'Start ', 'red', 6),        # Start condition at x=0, width=10
        (3.6, 'Slave Address', 'blue', 42),        # Slave address at x=10, width=20
        (46, 'Write ', 'purple', 5.6),          # Write bit at x=30, width=10
        (52, 'ACK', 'green', 6),                 # ACK at x=40, width=10
        (58.5, 'Register Address', 'orange', 46.9),   # Register address at x=50, width=30
        (106, 'ACK', 'green', 5.6),                 # ACK at x=80, width=10
        (111.9, 'Data ', 'brown',47.6),           # Data byte at x=90, width=30
        (159.9, 'NACK', 'green', 7.5),              # NACK at x=120, width=10
        (167.9, 'Stop ', 'red', 8)        # Stop condition at x=130, width=10
]

 # Create boxes and labels for each segment
    for x_pos, label, color, box_width in segments:
        # Create a rectangle that covers the entire SCL and SDA signal heights
        #alpha=0.3//for the color brightiness
        #sda_offset + 1.5//for the color from up the size
        #x_pos, -0.5//the colored box moving
        rect_height = 2.7  # Set the desired height of the rectangle
        y_start = -0.1     # Set the starting y position of the rectangle (to control vertical position)
        rect = patches.Rectangle((x_pos, y_start), box_width, rect_height, fill=True, edgecolor=color, facecolor=color, alpha=0.4 )

        ax.add_patch(rect)
        
      
   # Add the label in the center of the box
        ax.text(x_pos + box_width / 2, sda_offset + 0.5, label, color='black', ha='center', va='center', fontsize=8)
    
  
# Add legend for colors
    legend_labels = [
        ('red', 'START/STOP condition'),
        ('blue', 'Slave Address'),
        ('purple', 'Write bit'),
        ('green', 'ACK/NACK'),
        ('orange', 'Register Address'),
        ('brown', 'Data Byte')
        
    ]

    # Create dummy lines for legend
    for color, label in legend_labels:
        ax.plot([], [], color=color, label=label)

    # Show the legend
    ax.legend(loc='upper right', fontsize=8)

    
    # Display the plot in the sidebar
    with st.sidebar:
         
         st.pyplot(fig)


  





########################################################################################
#READ OPERATION
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

# Define column widths: left is wider, right is smaller
col1, col2 = st.columns([3, 1])

def plot_i2c_read_waveform(i2c_address, register, data,operation='Read'):
    """Generate and plot the I2C/read waveform for a read operation with negative-edge triggering, using colors for each segment."""
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Initialize timing and signals for SCL and SDA
    timing = []
    scl = []  # SCL line
    sda = []  # SDA line
    colors = []  # Store color for each segment

    def append_timing_steps(steps, scl_state, sda_state, color):
        """Helper function to append timing steps to the waveform."""
        timing.extend([len(timing) + i for i in range(steps)])
        scl.extend([scl_state] * steps)
        sda.extend([sda_state] * steps)
        colors.extend([color] * steps)

    # START condition: SDA goes low while SCL is high (Red)
    append_timing_steps(3, 1, 1, 'red')  # Idle state (SDA = SCL = 1)
    append_timing_steps(3, 1, 0, 'red')  # Start condition (SDA falls)

   # Slave Address (Blue) + Write bit (Cyan)
    address_bits = [int(bit) for bit in f'{i2c_address:07b}']  # 7-bit address
    for bit in address_bits:
        append_timing_steps(3, 1, bit, 'blue')  # SCL high, set SDA to bit (setup data when SCL is high)
        append_timing_steps(3, 0, bit, 'blue')  # SCL low, hold SDA (sample data on falling edge)

    # Write bit (0) - Cyan
    append_timing_steps(3, 1, 0, 'purple')  # SCL high, set SDA to write bit (0)
    append_timing_steps(3, 0, 0, 'purple')  # SCL low, hold SDA (sample write bit)

    # ACK from slave (Green)
    append_timing_steps(3, 1, 0, 'green')  # SCL high, prepare for ACK
    append_timing_steps(3, 0, 0, 'green')  # SCL low, ACK is low (sample ACK on falling edge)

    # Register Address (Orange)
    register_bits = [int(bit) for bit in f'{register:08b}']
    for bit in register_bits:
        append_timing_steps(3, 1, bit, 'orange')  # SCL high, set SDA to bit (setup data)
        append_timing_steps(3, 0, bit, 'orange')  # SCL low, hold SDA (sample data)
 # ACK from slave (Green)
    append_timing_steps(3, 1, 0, 'green')  # SCL high, prepare for ACK
    append_timing_steps(3, 0, 0, 'green')  # SCL low, ACK is low (sample ACK on falling edge)

 # Slave Address (Blue) + Write bit (purple)
    address_bits = [int(bit) for bit in f'{i2c_address:07b}']  # 7-bit address
    for bit in address_bits:
        append_timing_steps(3, 1, bit, 'blue')  # SCL high, set SDA to bit (setup data when SCL is high)
        append_timing_steps(3, 0, bit, 'blue')  # SCL low, hold SDA (sample data on falling edge)

    # Read bit (1) - Cyan
    append_timing_steps(3, 1, 1, 'purple')  # SCL high, set SDA to write bit (0)
    append_timing_steps(3, 0, 1, 'purple')  # SCL low, hold SDA (sample write bit)


 # ACK from slave (Green)
    append_timing_steps(3, 1, 0, 'green')  # SCL high, prepare for ACK
    append_timing_steps(3, 0, 0, 'green')  # SCL low, ACK is low (sample ACK on falling edge)

# Data Byte (Purple)
    for byte in data:
        data_bits = [int(bit) for bit in f'{byte:08b}']
        for bit in data_bits:
            append_timing_steps(3, 1, bit, 'brown')  # SCL high, set SDA to bit (setup data)
            append_timing_steps(3, 0, bit, 'brown')  # SCL low, hold SDA (sample data)

    # NACK from master (Yellow)
    append_timing_steps(3, 1, 1, 'green')  # SCL high, prepare for NACK
    append_timing_steps(3, 0, 1, 'green')  # SCL low, NACK is high (sample NACK)

    # STOP condition: SDA goes high while SCL is high (Red)
    append_timing_steps(3, 0, 0, 'red')  # SCL low, prepare for stop
    append_timing_steps(3, 1, 1, 'red')  # Stop condition (SDA rises)

    # Generate timing values for the x-axis
    timing = np.arange(len(scl))

    # Offset SDA signal for separation
    sda_offset = 1.5
    sda = [x + sda_offset for x in sda]

    # Plotting the SCL and SDA signals with colors for each segment
    for i in range(len(timing) - 1):
        ax.step(timing[i:i+2], scl[i:i+2], color=colors[i], lw=2)
        ax.step(timing[i:i+2], sda[i:i+2], color=colors[i], lw=2)

   # Add labels and grid
    ax.set_title("I2C Read Operation ")
    ax.set_xlabel("Time (us)")
    ax.set_ylabel("Signal Logical Level")
    ax.set_ylim(-1, sda_offset + 2.1)
    ax.grid(True)
# Add labels for SCL and SDA lines
    ax.text(0, 1, 'SCL', color='black', ha='right', va='center', fontsize=8)
    ax.text(0, sda_offset + 1, 'SDA', color='black', ha='right', va='center', fontsize=8)

# Draw boxes for each I2C segment (covering the whole signal height)
    segments = [
       (-3, 'Start ', 'red', 6),        # Start condition at x=0, width=10
        (3.6, 'Slave Address', 'blue', 42),        # Slave address at x=10, width=20
        (46, 'Write ', 'purple', 5.6),          # Write bit at x=30, width=10
        (52.1, 'ACK', 'green', 5),                 # ACK at x=40, width=10
        (57.8, 'Register Address', 'orange', 47.4),   # Register address at x=50, width=30
        (105.9, 'ACK', 'green', 5),                 # ACK at x=80, width=10
        (111.4, 'Slave Address', 'blue', 48),        # Slave address at x=10, width=20
        (159.9, 'read ', 'purple', 5.6),          # Write bit at x=30, width=10
        (166.1, 'ACK', 'green', 5.2),                 # ACK at x=40, width=10
        (171.8, 'Data ', 'brown',47.6),           # Data byte at x=90, width=30
        (219.9, 'NACK', 'green', 2.7),              # NACK at x=120, width=10
        (223.3, 'Stop ', 'red', 8)        # Stop condition at x=130, width=10
]

 # Create boxes and labels for each segment
    for x_pos, label, color, box_width in segments:
        # Create a rectangle that covers the entire SCL and SDA signal heights
        #alpha=0.3//for the color brightiness
        #sda_offset + 1.5//for the color from up the size
        #x_pos, -0.5//the colored box moving
        rect_height = 2.7  # Set the desired height of the rectangle
        y_start = -0.1     # Set the starting y position of the rectangle (to control vertical position)
        rect = patches.Rectangle((x_pos, y_start), box_width, rect_height, fill=True, edgecolor=color, facecolor=color, alpha=0.4 )

        ax.add_patch(rect)
        
      
   # Add the label in the center of the box
        ax.text(x_pos + box_width / 2, sda_offset + 0.5, label, color='black', ha='center', va='center', fontsize=8)


# Add legend for colors
    legend_labels = [
        ('red', 'START/STOP condition'),
        ('blue', 'Slave Address'),
        ('purple', 'Write bit'),
        ('green', 'ACK/NACK'),
        ('orange', 'Register Address'),
        ('brown', 'Data Byte')
        
    ]

    # Create dummy lines for legend
    for color, label in legend_labels:
        ax.plot([], [], color=color, label=label)

    # Show the legend
    ax.legend(loc='upper right', fontsize=8)

 # Display the plot in the sidebar
    with st.sidebar:
        st.pyplot(fig)





###########################no waveform, but the message is good
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# Initialize session state variables if they don't exist
if 'data_bytes' not in st.session_state:
    st.session_state.data_bytes = None
if 'log_list' not in st.session_state:
    st.session_state.log_list = []

# Creating the two tabs
#tab1, tab2 = st.tabs(["SLAVE MAIN💡", "Read Register📖"])

# TAB 1: SLAVE MAIN
#with tab1:
    # Define column widths: left is wider, right is smaller
    col1, col2 = st.columns([3, 1])

import streamlit as st

def check_hot_value(selected_data):
    # Convert selected data to integer if it's binary
    if isinstance(selected_data, str) and selected_data.isdigit():
        data_value = int(selected_data, 2)
    else:
        data_value = int(selected_data)

    # Check if the data has exactly one bit set
    return (data_value > 0) and (data_value & (data_value - 1)) == 0

# Function to display the main section for SLAVE MAIN.
def display_slave_main_section():
    # First column with four sub-columns
    col1, col2 = st.columns([3, 1])  # First column larger than second
    data_bytes = None  # Initialize data_bytes at the start
with col1:
        # Create 4 horizontal columns
        sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4)

# In column 1: Input for I2C Address
with sub_col1:
    i2c_address = st.text_input('I2C Address (Hex):', '68', key='i2c_address')
    try:
        i2c_address_int = int(i2c_address, 16)
        if not (0 <= i2c_address_int <= 0x7F):
            raise ValueError("I2C address out of range (0-127).")
    except ValueError:
        st.error("Invalid I2C address. Please provide a valid hexadecimal value (00-7F).")

# In column 2: Input for Register Address
with sub_col2:
    register_address = st.text_input('Register Address (Hex):', '00', key='register_address')
    try:
        register_address_int = int(register_address, 16)
        if not (0 <= register_address_int <= 0xFF):
            raise ValueError("Register address out of range (00-FF).")
    except ValueError as e:
        st.error(f"Invalid Register Address: {e}")

# In column 3: Data Selection
with sub_col3:
    HEX_NUMBERS = [f'{i:02X}' for i in range(256)]
    selected_data_slave_main = st.selectbox('Data(Hex):', HEX_NUMBERS, key='hex_data')

    # Check if the register address is 0x02, 0x03, 0x04, or 0x05 and validate the selected data
    if register_address.upper() in ['02', '03', '04', '05']:
        if not check_hot_value(selected_data_slave_main):
            st.error("Warning: the selected value is not allowed. Only one hot code is allowed")

# Convert selected data to an integer
try:
    data_to_send_slave_main = int(selected_data_slave_main, 16)

    # Check if the data is a "hot" value before proceeding, only for specific registers
    if register_address_int in [0x02, 0x03, 0x04, 0x05]:
        if check_hot_value(selected_data_slave_main):
            data_bytes = [data_to_send_slave_main]  # Assuming it's a list of bytes
        else:
            data_bytes = None  # Explicitly set to None if not a hot value
    else:
        data_bytes = [data_to_send_slave_main]  # Allow data for other registers

except ValueError as e:
    st.error(f"Error converting data: {e}")
    data_bytes = None

# Send Data Button in column 4
with sub_col4:
    if st.button('Send Data', key='send_data_button'):
        if data_bytes is not None:
            try:
                port = controller.get_port(i2c_address_int)
                combined_bytes = [register_address_int] + data_bytes
                port.write(combined_bytes)
                st.success('Data sent successfully to SLAVE MAIN ✔️')

                # Display the write waveform in the sidebar only if valid data exists
                if data_bytes:  # Ensure data_bytes is valid for plotting
                    plot_i2c_write_waveform(i2c_address_int, register_address_int, data_bytes, operation='write')

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("No valid data to send.")  # Triggered for specific registers (0x02, 0x03, etc.)

# Read Register Button in column 5
#with col5:
    if st.button('Read Register', key='read_register_button'):
        try:
            read_data = read_register_with_repeated_start(i2c_address_int, register_address)

            if read_data:
                read_data_display = read_data.hex().upper()

                # Plot the read waveform only if valid data was received
                if read_data:  # Ensure valid read data exists
                    plot_i2c_read_waveform(i2c_address_int, register_address_int, data_bytes, operation='read')

                # Shrink text area for read data
                st.text_area('Read Data:', value=read_data_display, height=60)

            else:
                st.error("No data received from the register.")

        except Exception as e:
            st.error(f"Error reading register: {e}")



# Reduce the size of the columns
#col1, col2 = st.columns([3,1])  # Make col2 smaller and leave space for col1

with col2:
    # Input for I2C Address
    i2c_address_input = st.text_input('Enter I2C Address (e.g., 68):', '68')
    try:
        i2c_address_int = int(i2c_address_input.strip(), 16)
        if not (0 <= i2c_address_int <= 0x7F):
            raise ValueError("I2C address out of range (0-127).")
        st.session_state.i2c_address_int = i2c_address_int
    except ValueError:
        st.error("Invalid I2C address. Please provide a valid hexadecimal value (0-7F).")

    
    registers_input = st.text_input('Enter Registers to Test (comma separated, e.g., 00,01):', '00', key='write_registers_input')
    registers = [int(register.strip(), 16) for register in registers_input.split(',')]
    
    if st.button('Test Write Registers', key='write_test'):
        if 'i2c_address_int' in st.session_state:
            write_results = test_write_registers(st.session_state.i2c_address_int, registers)
            st.write(write_results)
        else:
            st.error("Please enter a valid I2C address first.")
    
    # Read Operation Test
    st.markdown("<h3 style='font-size:16px;'>READ OPERATION TEST</h3>", unsafe_allow_html=True)
    registers_input = st.text_input('Enter Registers to Test (comma separated, e.g., 00,01):', '00', key='read_registers_input')
    registers = [int(register.strip(), 16) for register in registers_input.split(',')]
    
    if st.button('Test Read Registers', key='read_test'):
        if 'i2c_address_int' in st.session_state:
            read_results = test_read_registers(st.session_state.i2c_address_int, registers)
            st.write(read_results)
        else:
            st.error("Please enter a valid I2C address first.")
    
    # Multiple Address Random Test
    st.markdown("<h3 style='font-size:16px;'>MULTIPLE ADDRESS RANDOM TEST</h3>", unsafe_allow_html=True)
    i2c_addresses_input = st.text_input('Enter Multiple I2C Addresses (comma separated, e.g., 68,6A):', '68,6A', key='multiple_i2c_addresses_input')
    i2c_addresses = [int(addr.strip(), 16) for addr in i2c_addresses_input.split(',')]
    registers_input = st.text_input('Enter Registers to Test (comma separated, e.g., 00,01):', '00', key='registers_input_for_multiple_test')
    registers = [int(register.strip(), 16) for register in registers_input.split(',')]
    
    if st.button('Test Random Write/Read Operations (2000 Iterations)', key='multiple_random_test'):
        random_results = test_random_operations_multiple_addresses(i2c_addresses, registers)
        random_results_df = pd.DataFrame(random_results)
        st.dataframe(random_results_df, height=400, width=800)
# Call the display function
display_slave_main_section()
###############################################################################################


import time
import streamlit as st
from datetime import datetime

# Define the test points
def uvlo_tp():
    try:
        port = controller.get_port(i2c_address_int)
        
        port.write([0x00, 0x00])  # Writing 0x00 to register 0x00
        port.write([0x01, 0x01])  # Writing 0x02 to register 0x01
        port.write([0x02, 0x00])  # Writing 0x00 to register 0x02
        port.write([0x03, 0x0A])  # Writing 0x0A to register 0x03

        st.sidebar.write("TP1 executed successfully ✅ ")
        log_operations([(0x00, 0x00), (0x01, 0x02), (0x02, 0x00), (0x03, 0x0A)])
    except I2cNackError as e:
        st.sidebar.error(f"No acknowledgment received: {e}")
        log_error('N/A', f'I2C NACK error: {str(e)}')
    except Exception as e:
        st.sidebar.error(f"An error occurred: {str(e)}")
        log_error('N/A', f'Error: {str(e)}')

def ldo_tp():
    try:
        port = controller.get_port(i2c_address_int)
        
        port.write([0x00, 0x00])  # Writing 0x00 to register 0x00
        port.write([0x01, 0x02])  # Writing 0x04 to register 0x01
        port.write([0x02, 0x00])  # Writing 0x00 to register 0x02
        port.write([0x03, 0x0B])  # Writing 0x0B to register 0x03

        st.sidebar.write("TP2 executed successfully ✅ ")
        log_operations([(0x00, 0x00), (0x01, 0x04), (0x02, 0x00), (0x03, 0x0B)])
    except I2cNackError as e:
        st.sidebar.error(f"No acknowledgment received: {e}")
        log_error('N/A', f'I2C NACK error: {str(e)}')
    except Exception as e:
        st.sidebar.error(f"An error occurred: {str(e)}")
        log_error('N/A', f'Error: {str(e)}')

def noc_tp():
    try:
        port = controller.get_port(i2c_address_int)
        
        port.write([0x00, 0x00])  # Writing 0x00 to register 0x00
        port.write([0x01, 0x04])  # Writing 0x20 to register 0x01
        port.write([0x02, 0x00])  # Writing 0x00 to register 0x02
        port.write([0x03, 0x0C])  # Writing 0x0C to register 0x03

        st.sidebar.write("TP3 executed successfully ✅ ")
        log_operations([(0x00, 0x00), (0x01, 0x20), (0x02, 0x00), (0x03, 0x0C)])
    except I2cNackError as e:
        st.sidebar.error(f"No acknowledgment received: {e}")
        log_error('N/A', f'I2C NACK error: {str(e)}')
    except Exception as e:
        st.sidebar.error(f"An error occurred: {str(e)}")
        log_error('N/A', f'Error: {str(e)}')

def i2c_tp():
    try:
        port = controller.get_port(i2c_address_int)
        
        port.write([0x00, 0x00])  # Writing 0x00 to register 0x00
        port.write([0x01, 0x08])  # Writing 0x40 to register 0x01
        port.write([0x02, 0x00])  # Writing 0x00 to register 0x02
        port.write([0x03, 0x0D])  # Writing 0x0D to register 0x03

        st.sidebar.write("TP4 executed successfully ✅ ")
        log_operations([(0x00, 0x00), (0x01, 0x40), (0x02, 0x00), (0x03, 0x0D)])
    except I2cNackError as e:
        st.sidebar.error(f"No acknowledgment received: {e}")
        log_error('N/A', f'I2C NACK error: {str(e)}')
    except Exception as e:
        st.sidebar.error(f"An error occurred: {str(e)}")
        log_error('N/A', f'Error: {str(e)}')





def EN_REG():
    try:
        port = controller.get_port(i2c_address_int)
        
        # Writing 0x01 to register 0x00 to set the first bit (hot one)
        port.write([0x00, 0x01])  
        
        # Writing 0x02 to register 0x01 to set the second bit (hot one)
        port.write([0x01, 0x02]) 
        
        st.sidebar.write("EN_REG executed successfully ✅ ")
        log_operations([(0x00, 0x01), (0x01, 0x02)])  # Log the values written
    except I2cNackError as e:
        st.sidebar.error(f"No acknowledgment received: {e}")
        log_error('N/A', f'I2C NACK error: {str(e)}')
    except Exception as e:
        st.sidebar.error(f"An error occurred: {str(e)}")
        log_error('N/A', f'Error: {str(e)}')


def BYPASS_REG():
    try:
        port = controller.get_port(i2c_address_int)
        
        # Writing hot one values to registers
        port.write([0x06, 0x04])  # Writing 0x04 to register 0x02 (third bit set)
        port.write([0x07, 0x08])  # Writing 0x08 to register 0x03 (fourth bit set)
        
        st.sidebar.write("BYPASS_REG executed successfully ✅ ")
        log_operations([(0x06, 0x04), (0x07, 0x08)])  # Log the values written
    except I2cNackError as e:
        st.sidebar.error(f"No acknowledgment received: {e}")
        log_error('N/A', f'I2C NACK error: {str(e)}')
    except Exception as e:
        st.sidebar.error(f"An error occurred: {str(e)}")
        log_error('N/A', f'Error: {str(e)}')



def TEST_REG_A():
    try:
        port = controller.get_port(i2c_address_int)
        
        # Writing the next hot one values to registers
        port.write([0x04, 0x10])  # Writing 0x10 to register 0x04 (fifth bit set)
        port.write([0x05, 0x20])  # Writing 0x20 to register 0x05 (sixth bit set)
        
        st.sidebar.write("TEST_REG_A executed successfully ✅ ")
        log_operations([(0x04, 0x10), (0x05, 0x20)])  # Log the values written
    except I2cNackError as e:
        st.sidebar.error(f"No acknowledgment received: {e}")
        log_error('N/A', f'I2C NACK error: {str(e)}')
    except Exception as e:
        st.sidebar.error(f"An error occurred: {str(e)}")
        log_error('N/A', f'Error: {str(e)}')



def TEST_REG_D():
    try:
        port = controller.get_port(i2c_address_int)
        
        # Writing the next hot one values to registers
        port.write([0x02, 0x40])  # Writing 0x40 to register 0x06 (seventh bit set)
        port.write([0x03, 0x80])  # Writing 0x80 to register 0x07 (eighth bit set)
        
        st.sidebar.write("TEST_REG_D executed successfully ✅ ")
        log_operations([(0x02, 0x40), (0x03, 0x80)])  # Log the values written
    except I2cNackError as e:
        st.sidebar.error(f"No acknowledgment received: {e}")
        log_error('N/A', f'I2C NACK error: {str(e)}')
    except Exception as e:
        st.sidebar.error(f"An error occurred: {str(e)}")
        log_error('N/A', f'Error: {str(e)}')




def BUCK_REG():
    try:
        port = controller.get_port(i2c_address_int)
        
        # Writing the 6-bit number (010010) which is 0x12 in hexadecimal to register 0x08
        port.write([0x08, 0x12])
        
        st.sidebar.write("BUCK_REG executed successfully ✅ ")
        log_operations([(0x08, 0x12)])  # Log the value written
    except I2cNackError as e:
        st.sidebar.error(f"No acknowledgment received: {e}")
        log_error('N/A', f'I2C NACK error: {str(e)}')
    except Exception as e:
        st.sidebar.error(f"An error occurred: {str(e)}")
        log_error('N/A', f'Error: {str(e)}')


def log_operations(operations):
    for reg, val in operations:
        st.session_state.log_list.append({
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'address': f'{i2c_address_int:02X}',
            'register': f'{reg:02X}',
            'value': f'{val:02X}',
            'operation': 'Write'
        })

def log_error(register, error):
    st.session_state.log_list.append({
        'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'address': f'{i2c_address_int:02X}',
        'register': register,
        'value': 'N/A',
        'operation': error
    })

# Sidebar setup
st.sidebar.header("TEST POINTS ⚡")
selected_test_point = st.sidebar.selectbox(
    "Choose a Test Point:",
    ["Select",  "EN_REG" , "BYPASS_REG" , "TEST_REG_A" , "TEST_REG_D" , "BUCK_REG" ]
)

if st.sidebar.button("Send"):
    if selected_test_point == "EN_REG":
        EN_REG()
    elif selected_test_point == "BYPASS_REG":
        BYPASS_REG()
    elif selected_test_point == "TEST_REG_A":
        TEST_REG_A()
    elif selected_test_point == "TEST_REG_D":
        TEST_REG_D()
    elif selected_test_point == "BUCK_REG":
        BUCK_REG()
   
    else:
        st.sidebar.warning("Please select a valid test point.")


#########################################################################################################




# Static log panel in the sidebar
st.sidebar.header("Log Panel")
log_df = pd.DataFrame(st.session_state.log_list)
if 'datetime' in log_df.columns:
    log_df.rename(columns={'datetime': 'Date and Time'}, inplace=True)
    log_df = log_df[['Date and Time', 'address', 'register', 'value', 'operation']]
    log_df.rename(columns={'address': 'I2C Address'}, inplace=True)
    log_df = log_df.sort_values(by='Date and Time', ascending=False).reset_index(drop=True)  # Sort by Date and Time descending
    st.sidebar.markdown("""
        <style>
        .log-panel {
            max-height: 500px;
            overflow-y: auto;
        }
        </style>
        <div class="log-panel">
        """,
        unsafe_allow_html=True
    )
    st.sidebar.write(log_df)
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
else:
    st.sidebar.write("No logs available.")


#########################################################################################################
##############################
#with tab2:
    #st.subheader('Read Register ')

import time
import streamlit as st
from pyftdi.i2c import I2cNackError

# Define I2C address and registers
i2c_address = 0x68  # Example address
registers_to_check = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]  # List of registers to check

# Blink color dictionary for registers
blink_colors = {
    0x00: '🟣', 0x01: '🔵', 0x02: '🟡', 0x03: '🟠', 
    0x04: '🟤', 0x05: '🔶', 0x06: '🔴', 0x07: '🔵', 
    0x08: '🟡'
}

# Initialize session state
if 'register_states' not in st.session_state:
    st.session_state.register_states = {register: "🔴 N/A" for register in registers_to_check}
    st.session_state.register_values = {register: None for register in registers_to_check}

# Create a placeholder for the table
table_placeholder = st.empty()

# Function to read from a register
def read_register(i2c_address, register_address):
    try:
        st.session_state.register_states[register_address] = f"{blink_colors[register_address]} Checking"
        
        # Simulate I2C read
        port = controller.get_port(i2c_address)
        port.write([register_address], relax=False)
        read_data = port.read(1)
        
        # Store the read value in hex format
        read_value = read_data.hex().upper()  
        st.session_state.register_values[register_address] = f"h{read_value}"

        # Update register state to green
        st.session_state.register_states[register_address] = f"🟢 {st.session_state.register_values[register_address]}"
        return True
    except I2cNackError:
        st.session_state.register_states[register_address] = "🔴 N/A"
        return False

# Main loop: Read all registers every 2 seconds
while True:
    start_time = time.time()

    # Check all registers
    for register_address in registers_to_check:
        read_register(i2c_address, register_address)

    # Combine registers into 16-bit values
    r0_value = int(st.session_state.register_values[0x00][1:], 16) if st.session_state.register_values[0x00] else 0
    r1_value = int(st.session_state.register_values[0x01][1:], 16) if st.session_state.register_values[0x01] else 0
    en_reg_value = f"{(r1_value << 8) | r0_value:04X}"

    r2_value = int(st.session_state.register_values[0x02][1:], 16) if st.session_state.register_values[0x02] else 0
    r3_value = int(st.session_state.register_values[0x03][1:], 16) if st.session_state.register_values[0x03] else 0
    test_reg_d_value = f"{(r3_value << 8) | r2_value:04X}"

    r4_value = int(st.session_state.register_values[0x04][1:], 16) if st.session_state.register_values[0x04] else 0
    r5_value = int(st.session_state.register_values[0x05][1:], 16) if st.session_state.register_values[0x05] else 0
    test_reg_a_value = f"{(r5_value << 8) | r4_value:04X}"

    r6_value = int(st.session_state.register_values[0x06][1:], 16) if st.session_state.register_values[0x06] else 0
    r7_value = int(st.session_state.register_values[0x07][1:], 16) if st.session_state.register_values[0x07] else 0
    bypass_reg_value = f"{(r7_value << 8) | r6_value:04X}"

    buck_reg_value = st.session_state.register_values[0x08] if st.session_state.register_values[0x08] else "h00"

    # Create a hierarchical table format with hexadecimal notation
    table_content = f"""
<style>
    table, th, td {{
        border: 1px solid black;
        border-collapse: collapse;
        padding: 10px;
        text-align: center;
        margin: 0px;  /* Reduce margin */
        margin-left: -20px;  /* Move the table 20px to the right */
        margin-top: -490px;  /* Move the table upward by 50px */
    }}
    th {{
        background-color: #f2f2f2;
    }}
</style>



<table>
    <tr>
        <th colspan="2">EN_REG 0x{en_reg_value}</th>
        <th colspan="2">TEST_REG_D 0x{test_reg_d_value}</th>
        <th colspan="2">TEST_REG_A 0x{test_reg_a_value}</th>
        <th colspan="2">BYPASS_REG 0x{bypass_reg_value}</th>
        <th>BUCK_REG</th>
    </tr>
    <tr>
    <td>R1 {st.session_state.register_states[0x00]}</td>
    <td>R0 {st.session_state.register_states[0x01]}</td>
    <td>R3 {st.session_state.register_states[0x02]}</td>
    <td>R2 {st.session_state.register_states[0x03]}</td>
    <td>R5 {st.session_state.register_states[0x04]}</td>
    <td>R4 {st.session_state.register_states[0x05]}</td>
    <td>R7 {st.session_state.register_states[0x06]}</td>
    <td>R6 {st.session_state.register_states[0x07]}</td>
    <td>R8 {st.session_state.register_states[0x08]}</td>
    </tr>
</table>
"""


    # Render the table in Streamlit using markdown
    table_placeholder.markdown(table_content, unsafe_allow_html=True)

    # Control refresh rate
    time.sleep(0.1)  

    # Ensure the cycle takes 2 seconds
    elapsed_time = time.time() - start_time
    if elapsed_time < 2:
        time.sleep(2 - elapsed_time)
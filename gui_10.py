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

# Create an I2C controller instance and configure it
controller = I2cController()
controller.configure(url='ftdi://ftdi:232h/1')
frequency = st.number_input('Set I2C Frequency (Hz):', min_value=1, max_value=3400000, value=100000, step=1)

#frequency = st.number_input('Set I2C Frequency (Hz):', min_value=1, max_value=1000000, value=100000, step=1)
controller.configure(url='ftdi://ftdi:232h/1', frequency=frequency)

# Constants
BINARY_NUMBERS = [format(i, '08b') for i in range(256)]
HEX_NUMBERS = [format(i, '02X') for i in range(256)]
DECIMAL_NUMBERS = [str(i) for i in range(256)]



# Initialize session state for logs if not already present
if 'log_list' not in st.session_state:
    st.session_state.log_list = []

def format_as_hex(value):
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


import streamlit as st
import pandas as pd
from datetime import datetime

# Define column widths: left is wider, right is smaller
col1, col2 = st.columns([3, 1])

import streamlit as st
import pandas as pd
from datetime import datetime

# Define column widths: left is wider, right is smaller
col1, col2 = st.columns([3, 1])

def display_slave_main_section():
    """Function to display the main section for SLAVE MAIN."""
    with col1:
        st.subheader('SLAVE MAIN 💡')

        # Input for I2C Address
        i2c_address = st.text_input('Enter I2C Address (in Hex):', '68')
        try:
            i2c_address_int = int(i2c_address, 16)
            if not (0 <= i2c_address_int <= 0x7F):
                raise ValueError("I2C address out of range (0-127).")
        except ValueError:
            st.error("Invalid I2C address. Please provide a valid hexadecimal value (0-7F).")
            return None

        # Register Index Type Selection
        st.markdown('<h2 style="font-size:14px;font-weight:bold;margin-bottom:-10px;">Register Index Type</h2>', unsafe_allow_html=True)
        register_index_type = st.selectbox('Select Register Index Type:', ['8-bit', '16-bit'], key='register_index_type')

        # Input for Register Address
        register_address = st.text_input('Enter Register Address (in Hex):', '00')
        try:
            register_address_int = int(register_address, 16)
            if register_index_type == '8-bit' and not (0 <= register_address_int <= 0xFF):
                raise ValueError("Register address out of range for 8-bit index type")
            elif register_index_type == '16-bit' and not (0 <= register_address_int <= 0xFFFF):
                raise ValueError("Register address out of range for 16-bit index type")
        except ValueError as e:
            st.error(f"Invalid Register Address: {e}")
            return None

        # Data Type Selection
        st.markdown('<h2 style="font-size:14px;font-weight:bold;margin-bottom:-10px;">Data Type</h2>', unsafe_allow_html=True)
        selected_data_type = st.selectbox('', ['Binary', 'Hexadecimal', 'Decimal'], key='data_type')

        # Define Binary Data Options Based on Register Index Type
        if register_index_type == '8-bit':
            BINARY_NUMBERS = [f'{i:08b}' for i in range(256)]  # 8-bit binary numbers
        elif register_index_type == '16-bit':
            BINARY_NUMBERS = [f'{i:016b}' for i in range(65536)]  # 16-bit binary numbers

        # Data Selection
        if selected_data_type == 'Binary':
            selected_data_slave_main = st.selectbox('Select Binary Data:', BINARY_NUMBERS, key='binary_data')
        elif selected_data_type == 'Hexadecimal':
            if register_index_type == '16-bit':
                HEX_NUMBERS = [f'{i:04X}' for i in range(0x0000, 0xFFFF + 1)]  # 16-bit hexadecimal numbers with FF as last value
            else:
                HEX_NUMBERS = [f'{i:02X}' for i in range(256)]  # Default for other index types
            selected_data_slave_main = st.selectbox('Select Hexadecimal Data:', HEX_NUMBERS, key='hex_data')
        elif selected_data_type == 'Decimal':
            if register_index_type == '16-bit':
                DECIMAL_NUMBERS = [str(i) for i in range(0, 65536)]  # 16-bit decimal numbers with 65535 as last value
            else:
                DECIMAL_NUMBERS = [str(i) for i in range(256)]
            selected_data_slave_main = st.selectbox('Select Decimal Data:', DECIMAL_NUMBERS, key='decimal_data')

        if st.button('Send Data'):
            try:
                if selected_data_type == 'Binary':
                    data_to_send_slave_main = int(selected_data_slave_main, 2)
                elif selected_data_type == 'Hexadecimal':
                    data_to_send_slave_main = int(selected_data_slave_main, 16)
                elif selected_data_type == 'Decimal':
                    data_to_send_slave_main = int(selected_data_slave_main)
                else:
                    raise ValueError("Unsupported data type selected.")

                # Convert data to bytes based on index type
                if register_index_type == '8-bit':
                    data_bytes = [data_to_send_slave_main & 0xFF]
                elif register_index_type == '16-bit':
                    data_bytes = [
                        (data_to_send_slave_main >> 8) & 0xFF,
                        data_to_send_slave_main & 0xFF
                    ]

                # Ensure port.write() is handling the combined bytes correctly
                port = controller.get_port(i2c_address_int)
                combined_bytes = [register_address_int] + data_bytes
                port.write(combined_bytes)
                st.success('Data sent successfully to SLAVE MAIN ✔️')
                st.session_state.log_list.append({
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'address': f'{i2c_address_int:02X}',
                    'register': f'{register_address_int:02X}',
                    'value': format_as_hex(data_to_send_slave_main),
                    'operation': 'Write'
                })
            except I2cNackError as e:
                st.error(f"Error: {e}")
                st.session_state.log_list.append({
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'address': f'{i2c_address_int:02X}',
                    'register': f'{register_address_int:02X}',
                    'value': 'N/A',
                    'operation': 'I2C is not responding'
                })
            except ValueError as e:
                st.error(f"Error: {e}")

        if st.button('Read Register'):
            try:
                read_data = read_register_with_repeated_start(i2c_address_int, register_address)
                if read_data:
                    read_data_display = read_data.hex().upper()
                    st.text_area('Read Data:', value=read_data_display, height=100)
                else:
                    st.error("No data received from the register.")
            except Exception as e:
                st.error(f"Error reading register: {e}")

display_slave_main_section()


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
    
    # Write Operation Test
    st.markdown("<h3 style='font-size:20px;'>WRITE OPERATION TEST</h3>", unsafe_allow_html=True)
    registers_input = st.text_input('Enter Registers to Test (comma separated, e.g., 00,01):', '00', key='write_registers_input')
    registers = [int(register.strip(), 16) for register in registers_input.split(',')]
    
    if st.button('Test Write Registers', key='write_test'):
        if 'i2c_address_int' in st.session_state:
            write_results = test_write_registers(st.session_state.i2c_address_int, registers)
            st.write(write_results)
        else:
            st.error("Please enter a valid I2C address first.")
    
    # Read Operation Test
    st.markdown("<h3 style='font-size:20px;'>READ OPERATION TEST</h3>", unsafe_allow_html=True)
    registers_input = st.text_input('Enter Registers to Test (comma separated, e.g., 00,01):', '00', key='read_registers_input')
    registers = [int(register.strip(), 16) for register in registers_input.split(',')]
    
    if st.button('Test Read Registers', key='read_test'):
        if 'i2c_address_int' in st.session_state:
            read_results = test_read_registers(st.session_state.i2c_address_int, registers)
            st.write(read_results)
        else:
            st.error("Please enter a valid I2C address first.")
    
    # Multiple Address Random Test
    st.markdown("<h3 style='font-size:20px;'>MULTIPLE ADDRESS RANDOM TEST</h3>", unsafe_allow_html=True)
    i2c_addresses_input = st.text_input('Enter Multiple I2C Addresses (comma separated, e.g., 68,6A):', '68,6A', key='multiple_i2c_addresses_input')
    i2c_addresses = [int(addr.strip(), 16) for addr in i2c_addresses_input.split(',')]
    registers_input = st.text_input('Enter Registers to Test (comma separated, e.g., 00,01):', '00', key='registers_input_for_multiple_test')
    registers = [int(register.strip(), 16) for register in registers_input.split(',')]
    
    if st.button('Test Random Write/Read Operations (2000 Iterations)', key='multiple_random_test'):
        random_results = test_random_operations_multiple_addresses(i2c_addresses, registers)
        random_results_df = pd.DataFrame(random_results)
        st.dataframe(random_results_df, height=400, width=1000)

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
        port.write([0x02, 0x04])  # Writing 0x04 to register 0x02 (third bit set)
        port.write([0x03, 0x08])  # Writing 0x08 to register 0x03 (fourth bit set)
        
        st.sidebar.write("BYPASS_REG executed successfully ✅ ")
        log_operations([(0x02, 0x04), (0x03, 0x08)])  # Log the values written
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
        port.write([0x06, 0x40])  # Writing 0x40 to register 0x06 (seventh bit set)
        port.write([0x07, 0x80])  # Writing 0x80 to register 0x07 (eighth bit set)
        
        st.sidebar.write("TEST_REG_D executed successfully ✅ ")
        log_operations([(0x06, 0x40), (0x07, 0x80)])  # Log the values written
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
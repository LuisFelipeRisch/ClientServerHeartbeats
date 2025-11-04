import sys
import csv

def process_differences(input_file, output_file):
  """
  Processes a CSV file (delimited by ';') to calculate the difference
  between the 'SERVER_RECEIVED_AT_NS' of the current row and the previous one,
  and converts the result to milliseconds.

  Args:
    input_file (str): The path to the input CSV file.
    output_file (str): The path to the output TXT file to save results.
  """
  
  # Variable to store the previous row's value
  previous_server_time = None
  
  # List to store the results
  diff_results_ms = []

  print(f"Processing file: {input_file}...")

  try:
    with open(input_file, mode='r', encoding='utf-8') as infile:
      # Set up the CSV reader with the ';' delimiter
      reader = csv.reader(infile, delimiter=';')
      
      # Read the header to find the column index
      try:
        header = next(reader)
      except StopIteration:
        print("Error: The file is empty.")
        return

      try:
        # Find the index of the desired column
        server_time_index = header.index('SERVER_RECEIVED_AT_NS')
      except ValueError:
        print(f"Error: Column 'SERVER_RECEIVED_AT_NS' not found in the header.")
        print(f"Header found: {header}")
        return

      # Iterate over the remaining rows
      for i, row in enumerate(reader):
        try:
          # Get the value from the column and convert it to an integer
          current_server_time = int(row[server_time_index])
          
          # If it's not the first data row
          if previous_server_time is not None:
            # Calculate the difference in nanoseconds
            difference_ns = current_server_time - previous_server_time
            
            # **NOVA LINHA: Converte de nanosegundos para milissegundos**
            difference_ms = difference_ns
            
            # Adiciona o resultado em MS na lista
            diff_results_ms.append(difference_ms)
          
          # Update the previous value for the next iteration
          previous_server_time = current_server_time

        except (ValueError, TypeError):
          print(f"Warning: Skipping line {i+2} (header-inclusive). Non-numeric or malformed data: {row}")
        except IndexError:
          print(f"Warning: Skipping line {i+2}. Malformed row (incorrect number of columns).")

    # Escreve todos os resultados no arquivo de saída especificado.
    # O modo 'w' (write) CRIA o arquivo se ele não existir, ou o sobrescreve.
    with open(output_file, mode='w', encoding='utf-8') as outfile:
      outfile.write("Difference_MS\n") # Cabeçalho atualizado para MS
      for diff in diff_results_ms:
        outfile.write(f"{diff}\n") # Escreve o valor em milissegundos
    
    print(f"Processing complete!")
    print(f"Results (in milliseconds) saved to: {output_file}")

  except FileNotFoundError:
    print(f"Error: File '{input_file}' not found.")
  except PermissionError:
    print(f"Error: No permission to write to '{output_file}'.")
  except Exception as e:
    print(f"An unexpected error occurred: {e}")

# --- Start of Script Execution ---
if __name__ == "__main__":
  # Check if *two* arguments (input and output) were passed
  if len(sys.argv) != 3:
    print(f"Usage: python {sys.argv[0]} <input_filename.txt> <output_filename.txt>")
    sys.exit(1) # Exit the script if arguments are wrong
    
  input_filename = sys.argv[1]
  output_filename = sys.argv[2]
  
  process_differences(input_filename, output_filename)
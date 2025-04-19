RAW_TRACES_DIR_PATH   = "./traces_ufpr_lan/raw"
JACOBSON_DIR_PATH     = "./traces_ufpr_lan/jacobson"
ALPHA                 = 0.9
BETA                  = 4
CSV_SEPARATOR         = ";"
JACOBSON_EXTRA_HEADER = %w[MID_RANGE MEAN_DEVIATION TIMEOUT]

mid_range                = 0
mean_deviation           = 0
server_received_at_index = -1
is_first_data_point      = true

Dir.glob("#{RAW_TRACES_DIR_PATH}/*").each do |file_path|
  filename    = File.basename(file_path)
  line_number = 0

  File.open("#{JACOBSON_DIR_PATH}/#{filename}", "w") do |jacobson_file|
    File.foreach(file_path) do |line|
      line = line.chomp
      splitted_line = line.split(CSV_SEPARATOR)

      if line_number == 0
        server_received_at_index = splitted_line.index("SERVER_RECEIVED_AT_NS").to_i
        header = splitted_line + JACOBSON_EXTRA_HEADER
        jacobson_file.puts(header.join(CSV_SEPARATOR))
        line_number += 1
        next
      end

      server_received_at = splitted_line[server_received_at_index].to_i rescue 0

      if is_first_data_point
        mid_range           = server_received_at
        mean_deviation      = 0
        is_first_data_point = false
      else
        next_mean      = (mid_range - server_received_at).abs
        mean_deviation = (ALPHA * mean_deviation) + (1 - ALPHA) * next_mean
        mid_range      = (ALPHA * mid_range) + (1 - ALPHA) * server_received_at
      end

      timeout = mid_range + (BETA * mean_deviation)
      values  = [mid_range, mean_deviation, timeout]
      jacobson_file.puts((splitted_line + values).join(CSV_SEPARATOR))

      line_number += 1
    end
  end
end
require 'pry'

RAW_TRACES_DIR_PATH   = "./traces_ufpr_ufsm_week_day/raw"
JACOBSON_DIR_PATH     = "./traces_ufpr_ufsm_week_day/jacobson"
ALPHA                 = 0.9
BETA                  = 4
CSV_SEPARATOR         = ";"
JACOBSON_EXTRA_HEADER = %w[MID_RANGE MEAN_DEVIATION TIMEOUT]

mid_range                = -1
mean_deviation           = -1
server_received_at_index = -1
last_server_received_at  = -1

18.times do |index|
  filename    = "log_#{index}.txt"
  file_path   = "#{RAW_TRACES_DIR_PATH}/#{filename}"
  line_number = 0

  File.open("#{JACOBSON_DIR_PATH}/#{filename}", "w") do |jacobson_file|
    File.foreach(file_path) do |line|
      line          = line.chomp
      splitted_line = line.split(CSV_SEPARATOR)

      if line_number == 0
        server_received_at_index = splitted_line.index("SERVER_RECEIVED_AT_NS").to_i
        header                   = splitted_line + JACOBSON_EXTRA_HEADER
        jacobson_file.puts(header.join(CSV_SEPARATOR))
        line_number += 1
        next
      end

      server_received_at = splitted_line[server_received_at_index].to_i

      if last_server_received_at == -1
        values = [-1, -1, -1]
        jacobson_file.puts((splitted_line + values).join(CSV_SEPARATOR))
        line_number += 1
        last_server_received_at = server_received_at
        next
      end

      next_mean = server_received_at - last_server_received_at

      if mid_range == -1 && mean_deviation == -1
        mid_range      = next_mean
        mean_deviation = 0
      else
        mean_deviation = ALPHA * mean_deviation + (1 - ALPHA) * (mid_range - next_mean).abs
        mid_range      = ALPHA * mid_range + (1 - ALPHA) * next_mean
      end

      timeout = server_received_at + (mid_range + (BETA * mean_deviation))
      values  = [mid_range, mean_deviation, timeout]
      jacobson_file.puts((splitted_line + values).join(CSV_SEPARATOR))

      line_number             += 1
      last_server_received_at = server_received_at
    end
  end
end
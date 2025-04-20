RAW_TRACES_DIR_PATH   = "./traces_ufpr_lan/raw"
JACOBSON_DIR_PATH     = "./traces_ufpr_lan/jacobson_paper"
GAMA                  = 0.1
BETA                  = 1
PHI                   = 4
CSV_SEPARATOR         = ";"
JACOBSON_EXTRA_HEADER = %w[INTERVAL DELAY VARIATION TIMEOUT]

server_received_at_index   = -1
delay                      = 0
variation                  = 0
last_heartbeat_received_at = 0

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
        header = splitted_line + JACOBSON_EXTRA_HEADER
        jacobson_file.puts(header.join(CSV_SEPARATOR))
        line_number += 1
        next
      end

      server_received_at         = splitted_line[server_received_at_index].to_i
      interval                   = server_received_at - last_heartbeat_received_at
      delay                      = (1 - GAMA) * delay + GAMA * interval
      variation                  = (1 - GAMA) * variation + GAMA * (interval - delay).abs
      timeout                    = BETA * delay + PHI * variation
      last_heartbeat_received_at = server_received_at
      values                     = [interval, delay, variation, timeout]

      jacobson_file.puts((splitted_line + values).join(CSV_SEPARATOR))

      line_number += 1
    end
  end
end
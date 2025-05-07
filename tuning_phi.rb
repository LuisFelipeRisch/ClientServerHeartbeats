require 'pry'

RAW_TRACES_DIR_PATH   = "./traces_ufpr_ufsm_week_day/raw"
JACOBSON_DIR_PATH     = "./traces_ufpr_ufsm_week_day/jacobson"
PHI_MIN               = 1.0
PHI_MAX               = 4.0
ALPHA                 = 0.9
CSV_SEPARATOR         = ";"
JACOBSON_EXTRA_HEADER = %w[MID_RANGE MEAN_DEVIATION PHI TIMEOUT]

def greater_than?(a, b, epsilon = Float::EPSILON)
  (a - b) > epsilon
end

def less_than?(a, b, epsilon = Float::EPSILON)
  (b - a) > epsilon
end

mid_range                    = -1
mean_deviation               = -1
server_received_at_index     = -1
last_server_received_at      = -1
time_period                  = 1
time_period_mul_interval_sum = 0
time_period_sum              = 0
interval_sum                 = 0 
time_period_squared_sum      = 0

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
        values = [-1, -1, -1, -1]
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





# require 'pry'

# RAW_TRACES_DIR_PATH   = "./traces_ufpr_lan/raw"
# JACOBSON_DIR_PATH     = "./traces_ufpr_lan/tuning_phi"
# GAMA                  = 0.1
# BETA                  = 1.0
# PHI_MIN               = 1.0
# PHI_MAX               = 4.0
# CSV_SEPARATOR         = ";"
# JACOBSON_EXTRA_HEADER = %w[INTERVAL DELAY VARIATION PHI TIMEOUT]

# def greater_than?(a, b, epsilon = Float::EPSILON)
#   (a - b) > epsilon
# end

# def less_than?(a, b, epsilon = Float::EPSILON)
#   (b - a) > epsilon
# end

# server_received_at_index     = -1
# delay                        = 0
# variation                    = 0
# last_heartbeat_received_at   = 0
# time_period                  = 1
# time_period_mul_interval_sum = 0
# time_period_sum              = 0
# interval_sum                 = 0 
# time_period_squared_sum      = 0

# 18.times do |index|
#   filename    = "log_#{index}.txt"
#   file_path   = "#{RAW_TRACES_DIR_PATH}/#{filename}"
#   line_number = 0

#   File.open("#{JACOBSON_DIR_PATH}/#{filename}", "w") do |jacobson_file|
#     File.foreach(file_path) do |line|
#       line          = line.chomp
#       splitted_line = line.split(CSV_SEPARATOR)

#       if line_number == 0
#         server_received_at_index = splitted_line.index("SERVER_RECEIVED_AT_NS").to_i
#         header = splitted_line + JACOBSON_EXTRA_HEADER
#         jacobson_file.puts(header.join(CSV_SEPARATOR))
#         line_number += 1
#         next
#       end
      
#       server_received_at             = splitted_line[server_received_at_index].to_i
#       interval                       = server_received_at - last_heartbeat_received_at
#       delay                          = (1 - GAMA) * delay + GAMA * interval
#       variation                      = (1 - GAMA) * variation + GAMA * (interval - delay).abs
#       time_period_mul_interval_sum   += time_period * interval
#       time_period_sum                += time_period
#       interval_sum                   += interval
#       time_period_squared_sum        += time_period * time_period
#       linear_coefficient_denominator = ((time_period * time_period_squared_sum) - (time_period_sum * time_period_sum)).to_f
#       linear_coefficient             = 0.0

#       binding.pry unless linear_coefficient_denominator.positive? 

#       if linear_coefficient_denominator.positive? 
#         linear_coefficient = ((time_period * time_period_mul_interval_sum) - (time_period_sum * interval_sum)).to_f / 
#                              linear_coefficient_denominator                
#       end            
                                      
#       slope_coefficient              = (interval_sum - (linear_coefficient * time_period_sum)).to_f / 
#                                        time_period.to_f
#       trend                          = linear_coefficient + (slope_coefficient * time_period)
#       phi                            = (((trend + variation) - delay).abs / variation.to_f).ceil

#       if greater_than?(phi, PHI_MAX)
#         phi = PHI_MAX
#       end

#       if less_than?(phi, PHI_MIN)
#         phi = PHI_MIN
#       end

#       # binding.pry

#       timeout                    = BETA * delay + phi * variation
#       last_heartbeat_received_at = server_received_at
#       values                     = [interval, delay, variation, phi, timeout]

#       jacobson_file.puts((splitted_line + values).join(CSV_SEPARATOR))

#       line_number += 1
#       time_period += 1
#     end
#   end
# end
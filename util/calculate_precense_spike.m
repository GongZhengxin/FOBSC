function [t1,t2,spike_rates] = calculate_precense_spike(spike_times)

window_size = 60*1000;

start_time = spike_times(1);
end_time = spike_times(end);
time_windows = start_time:window_size:end_time;
spike_counts = zeros(size(time_windows));

for i = 1:length(time_windows)
    window_start = time_windows(i);
    window_end = window_start + window_size;
    spike_counts(i) = sum(spike_times >= window_start & spike_times < window_end);
    if(i==length(time_windows))
        last_window_size = end_time-window_start;
    end
end

spike_rates = 1000*spike_counts./window_size;
spike_rates(end) = spike_rates(end)*window_size/last_window_size;

valid_indices = spike_rates > 0.5;
valid_time_windows = time_windows(valid_indices);
valid_spike_rates = spike_rates(valid_indices);
if (isempty(valid_time_windows) || max(spike_rates)<1)
    t1=0;
    t2=0;
else
    max_length = 0;
    max_start_idx = 0;
    current_length = 0;
    current_start_idx = 0;

    for i = 1:length(valid_indices)
        if valid_indices(i)
            if current_length == 0
                current_start_idx = i;
            end
            current_length = current_length + 1;
        else
            if current_length > max_length
                max_length = current_length;
                max_start_idx = current_start_idx;
            end
            current_length = 0;
        end
    end

    if current_length > max_length
        max_length = current_length;
        max_start_idx = current_start_idx;
    end

    t1 = time_windows(max_start_idx);
    t2 = time_windows(max_start_idx + max_length - 1) + window_size;
end

end
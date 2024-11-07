function PostProcess_function(data_path)

cd(data_path)


meta_file = dir('processed/GoodUnitRaw*');
load(fullfile('processed',meta_file(1).name));

global_params.m_strctStimulusParams.onset_time = trial_ML(1).VariableChanges.onset_time;
global_params.m_strctStimulusParams.offset_time = trial_ML(1).VariableChanges.offset_time;
global_params.m_strImageListUsed = trial_ML(1).UserVars.DatasetName;

mkdir processed/data_viewer
load global_params.mat

pre_onset = global_params.pre_onset;
post_onset = global_params.post_onset;
psth_window_size_ms = global_params.psth_window_size_ms;
base_line_time = global_params.base_line_time;
high_line_time1 = global_params.high_line_time1;
high_line_time2 = global_params.high_line_time2;

good_idx = 1;
GoodUnitStrc = UnitStrc;
GoodUnitStrc(good_idx).Raster = [];
GoodUnitStrc(good_idx).img_idx = [];

trial_valid_idx = meta_data.trial_valid_idx;
onset_time_ms = meta_data.onset_time_ms;
img_size = meta_data.img_size;
for spike_num = 1:length(UnitStrc)
    spike_time = UnitStrc(spike_num).spiketime_ms;

    if(unitType(spike_num)==0)
        continue
    end
    
    psth_range = -pre_onset:post_onset;
    good_trial = find(trial_valid_idx);
    raster_raw = zeros([length(good_trial), pre_onset+post_onset]);
    for good_trial_idx = 1:length(good_trial)
        loc_in_orig = good_trial(good_trial_idx);
        onset_time_trial = onset_time_ms(loc_in_orig);
        time_bound = spike_time(spike_time>onset_time_trial-pre_onset & spike_time<onset_time_trial+post_onset);
        time_bound = 1+time_bound-(onset_time_trial-pre_onset);
        for time_bound_idx = 1:length(time_bound)
            raster_raw(good_trial_idx,floor(time_bound(time_bound_idx)))=raster_raw(good_trial_idx,floor(time_bound(time_bound_idx)))+1;
        end
    end

    img_idx = trial_valid_idx(good_trial);

    onset_t = zeros([1, img_size]);
    for img = 1:img_size
        onset_t(img) = sum(img_idx==img);
    end

    psth_raw = zeros(size(raster_raw));
    for time_points = 1:size(psth_raw,2)
        if(time_points-psth_window_size_ms/2<1)
            time_window = 1:psth_window_size_ms;
        elseif(time_points+psth_window_size_ms/2>size(psth_raw,2))
            time_winsow = size(psth_raw,2)-psth_window_size_ms:size(psth_raw,2);
        else
            time_window = time_points-psth_window_size_ms/2:time_points+psth_window_size_ms/2;
        end
        psth_raw(:,time_points) =1000*sum(raster_raw(:, time_window),2)/length(time_window);
    end

    response_matrix_img = zeros([img_size, pre_onset+post_onset]);
    for img = 1:img_size
        response_matrix_img(img,:) = sum(psth_raw(img_idx==img, :),1)./ onset_t(img);
    end

    baseline = sum(raster_raw(:,(base_line_time)+pre_onset+1),2);
    highline1 = sum(raster_raw(:,(high_line_time1)+pre_onset+1),2);
    highline2 = sum(raster_raw(:,(high_line_time2)+pre_onset+1),2);

    [p1,~,~] = ranksum(highline1,baseline,method="approximate");
    [p2,~,~] = ranksum(highline2,baseline,method="approximate");
    
    if(min(p1,p2) < (0.01/length(GoodUnitStrc)))
        GoodUnitStrc(good_idx).waveform = UnitStrc(spike_num).waveform;
        GoodUnitStrc(good_idx).spiketime_ms = UnitStrc(spike_num).spiketime_ms;
        GoodUnitStrc(good_idx).spikepos = UnitStrc(spike_num).spikepos;
        GoodUnitStrc(good_idx).amplitudes = UnitStrc(spike_num).amplitudes;
        GoodUnitStrc(good_idx).kslabel = UnitStrc(spike_num).kslabel;
        GoodUnitStrc(good_idx).Raster = uint8(raster_raw);
        GoodUnitStrc(good_idx).img_idx = img_idx;
        GoodUnitStrc(good_idx).response_matrix_img = response_matrix_img;
        GoodUnitStrc(good_idx).firing_rate = UnitStrc(spike_num).firing_rate;
        GoodUnitStrc(good_idx).presence_ratio = UnitStrc(spike_num).presence_ratio;   
        GoodUnitStrc(good_idx).ISI_violations = UnitStrc(spike_num).ISI_violations;
        GoodUnitStrc(good_idx).qm = qMetric(spike_num,:);
        GoodUnitStrc(good_idx).unittype = unitType(spike_num);
        good_idx = good_idx+1;
    end
    fprintf('%d good, look %d in %d \n', good_idx-1,spike_num,length(UnitStrc))
end
GoodUnitStrc(good_idx:end)=[];
global_params.PsthRange = psth_range(2:end);

file_name_LOCAL = fullfile('processed',sprintf('GoodUnit_%s_g%s.mat',meta_file(1).name(13:end-7), meta_data.g_number));
save(file_name_LOCAL, "GoodUnitStrc", "trial_ML","global_params",'meta_data','-v7.3')
end
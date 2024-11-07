log_file = [pwd, '\\process.log'];
nas_location = 'Z:\Monkey_ephys\NPX_Processed';
nas_location_raster = 'Z:\Monkey_ephys\NPXRaster_Pool';
meta_file = dir('processed/META*');
load(fullfile('processed',meta_file(1).name));
meta_data = load(fullfile('processed',meta_file(1).name));
ML_FILE = dir("processed\ML*");
trial_ML = load(fullfile('processed',ML_FILE(1).name)).trial_ML;
[UnitStrc] = load_KS4_output('./kilosort_def_5block_97',IMEC_AP_META,SyncLine);

for trial_idx = 1:length(trial_ML)
    trial_ML(trial_idx).AnalogData.Mouse=[];
    trial_ML(trial_idx).AnalogData.KeyInput=[];
end

file_name_LOCAL = fullfile('processed',sprintf('GoodUnitRaw_%s_g%s.mat',meta_file(1).name(6:end-4), meta_data.g_number));
save(file_name_LOCAL, "UnitStrc", "trial_ML",'meta_data','-v7.3')
% file_name_NAS = fullfile(nas_location, sprintf('GoodUnitRaw_%s_g%s.mat',meta_file(1).name(6:end-4), meta_data.g_number));
% copyfile(file_name_LOCAL,file_name_NAS)

meta_file = dir('processed/GoodUnitRaw*');
load(fullfile('processed',meta_file(1).name));

global_params.m_strctStimulusParams.onset_time = trial_ML(1).VariableChanges.onset_time;
global_params.m_strctStimulusParams.offset_time = trial_ML(1).VariableChanges.offset_time;
global_params.m_strImageListUsed = trial_ML(1).UserVars.DatasetName;

mkdir processed/data_viewer
%%
if ~exist('pre_onset', 'var')
    pre_onset = 50;
end
global_params.pre_onset = pre_onset;
if ~exist('post_onset', 'var')
    post_onset = 300;
end
global_params.post_onset = post_onset;
good_idx = 1;

if ~exist('psth_window_size_ms', 'var')
    psth_window_size_ms = 20;
end

switch global_params.m_strctStimulusParams.onset_time
    case 150
        base_line_time = -25:25;
        high_line_time = 60:180;
    case 200
        base_line_time = -25:25;
        high_line_time = 70:250;
    case 250
        base_line_time = -25:25;
        high_line_time = 60:280;
    otherwise

end

global_params.psth_window_size_ms = psth_window_size_ms;
global_params.base_line_time = base_line_time;
global_params.high_line_time = high_line_time;

figure
set(gcf,'Position',[50 400 1800 650])
GoodUnitStrc = UnitStrc;
% GoodUnitStrc(good_idx).PSTH =[];
GoodUnitStrc(good_idx).Raster = [];
GoodUnitStrc(good_idx).img_idx = [];

trial_valid_idx = meta_data.trial_valid_idx;
onset_time_ms = meta_data.onset_time_ms;
img_size = meta_data.img_size;
for spike_num = 1:length(UnitStrc)
    spike_time = UnitStrc(spike_num).spiketime_ms;
    [t1,t2,spike_rates] = calculate_precense_spike(spike_time);
    if(t1==0 || t2 ==0)
        continue
    end
    valid_trial_this_neuron=zeros(size(meta_data.trial_valid_idx));
    for trial_idx = 1:length(meta_data.trial_valid_idx)
        onset_time_trial = onset_time_ms(trial_idx);
        if(onset_time_trial>t1 && onset_time_trial<t2)
            valid_trial_this_neuron(trial_idx)=1;
        end
    end

    psth_range = -pre_onset:post_onset;
    good_trial = find(trial_valid_idx & valid_trial_this_neuron);
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
    if(min(onset_t)<3)
        continue
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

    baseline = psth_raw(:,(base_line_time)+pre_onset+1);
    highline = psth_raw(:,(high_line_time)+pre_onset+1);

    [p,h,stats] = ranksum(highline(:),baseline(:),method="approximate");
    if(p<0.0001)
        
        subplot(2,5,1)
        wdata = UnitStrc(spike_num).waveform;
        [a,b]=find(abs(wdata) == max(abs(wdata(:))));
        useful_idx = find((wdata(1,:)~=0));
        useful_idx = useful_idx(mod(useful_idx-b,2)==0);
        hori_val = useful_idx-min(useful_idx);
        plot(wdata(:,useful_idx)-hori_val/10,'k')
        title(sprintf('Amp = %.02f uv\n', mean(UnitStrc(spike_num).amplitudes)))

        subplot(2,5,[2,3])
        imagesc(1:img_size,-pre_onset:post_onset,response_matrix_img')
        colorbar;
        clim([0, quantile(response_matrix_img(:), 0.99999)])

        subplot(2,5,[4,5]);
        hold off
        plot(0,0)
        hold on
        shadedErrorBar(psth_range(2:end),mean(psth_raw),std(psth_raw)./sqrt(size(psth_raw,1))); hold on
        plot([base_line_time([1,end])],[ mean(baseline(:)), mean(baseline(:))],'k','LineWidth',2)
        plot([high_line_time([1,end])],[ mean(highline(:)), mean(highline(:))],'k','LineWidth',2)
        ylim([min(mean(psth_raw))-1,max(mean(psth_raw))+1])

        subplot(2,5,8);
        plot(onset_t)
        sgtitle(sprintf('Visual Response Unit No.%d, KSlabel = %s', good_idx, UnitStrc(spike_num).kslabel))

        subplot(2,5,[6]);
        within_loc = find(spike_time>t1 &spike_time<t2);
        isi = diff(spike_time(within_loc));
        isi(isi>18)=18;
        violate_rate = sum(isi<1.2)./length(isi);
        hist([isi;-isi],40)
        xlim([-15,15])
        title(sprintf('ISI < 1.2 ms = %.02f percent', 100*violate_rate))

        subplot(2,5,7);
        hold off
        plot(spike_rates); hold on
        xline(t1/60000); xline(t2/60000)

        drawnow
        saveas(gcf,sprintf('processed/data_viewer/%03d.png', good_idx))

        GoodUnitStrc(good_idx).waveform = UnitStrc(spike_num).waveform;
        GoodUnitStrc(good_idx).spiketime_ms = UnitStrc(spike_num).spiketime_ms;
        GoodUnitStrc(good_idx).spikepos = UnitStrc(spike_num).spikepos;
        GoodUnitStrc(good_idx).amplitudes = UnitStrc(spike_num).amplitudes;
        GoodUnitStrc(good_idx).kslabel = UnitStrc(spike_num).kslabel;
        GoodUnitStrc(good_idx).Raster = uint8(raster_raw);
        GoodUnitStrc(good_idx).img_idx = img_idx;
        GoodUnitStrc(good_idx).response_matrix_img = response_matrix_img;
        good_idx = good_idx+1;
    end
    log_message(log_file, sprintf('%d good, look %d in %d \n', good_idx-1,spike_num,length(UnitStrc)))
end
GoodUnitStrc(good_idx:end)=[];
global_params.PsthRange = psth_range(2:end);


file_name_LOCAL = fullfile('processed',sprintf('GoodUnit_%s_g%s.mat',meta_file(1).name(13:end-7), meta_data.g_number));
save(file_name_LOCAL, "GoodUnitStrc", "trial_ML","global_params",'meta_data','-v7.3')

% file_name_NAS = fullfile(nas_location,sprintf('GoodUnit_%s_g%s.mat',meta_file(1).name(13:end-7), meta_data.g_number));
% copyfile(file_name_LOCAL,file_name_NAS)
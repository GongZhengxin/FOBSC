cd(data_path)
close all

meta_file = dir('processed/GoodUnitRaw*');
load(fullfile('processed',meta_file(1).name));

global_params.m_strctStimulusParams.onset_time = trial_ML(1).VariableChanges.onset_time;
global_params.m_strctStimulusParams.offset_time = trial_ML(1).VariableChanges.offset_time;
global_params.m_strImageListUsed = trial_ML(1).UserVars.DatasetName;

%%

pre_onset = 300;
global_params.pre_onset = pre_onset;
post_onset = 400;
global_params.post_onset = post_onset;

%% load LFP
SGLX_Folder = dir('NPX*');
session_name = SGLX_Folder(1).name;
LFPFileName=dir(fullfile(session_name, '*imec*'));
[LFP_META, LF_SIGNAL] = load_LFP_data(pwd);

trial_valid_idx = meta_data.trial_valid_idx;
onset_time_ms = meta_data.onset_time_ms;
img_size = meta_data.img_size;

%% this is the time point of image onset in imec time scale
onset_time_ms = interp1(meta_data.SyncLine.NI_time, meta_data.SyncLine.imec_time,onset_time_ms);
psth_range = -pre_onset:(1000/LFP_META.lfp_sr):post_onset;

pre_onset_sample_point = pre_onset/(1000/LFP_META.lfp_sr);
post_onset_sample_point = post_onset/(1000/LFP_META.lfp_sr);
LFP_data_trial_wise = zeros([length(onset_time_ms),size(LF_SIGNAL,1), length(psth_range)]);
for onset_time_idx = 1:length(onset_time_ms)
    onset_time_trial = onset_time_ms(onset_time_idx);
    onset_time_trial_in_lfp = round(onset_time_trial/(1000/LFP_META.lfp_sr));
    interested_time = onset_time_trial_in_lfp+[-pre_onset_sample_point:post_onset_sample_point];
    LFP_data_trial_wise(onset_time_idx, :,:) = LF_SIGNAL(:, interested_time);
end
LFP_data_img_wise =  zeros([img_size,size(LF_SIGNAL,1), length(psth_range)]);
for img = 1:img_size
    LFP_data_img_wise(img,:,:) = mean(LFP_data_trial_wise(trial_valid_idx==img, :,:),1);
end
figure;
imagesc(psth_range, LFP_META.depth_vals, squeeze(mean(LFP_data_img_wise,1)));
xlim([0,300]);
set(gcf,'Position',[800 600 500 400])
saveas(gcf,'processed/LF.fig')
global_params.PsthRange = psth_range;
file_name_LOCAL = fullfile('processed',sprintf('GoodLFP_%s_g%s.mat',meta_file(1).name(13:end-7), meta_data.g_number));
save(file_name_LOCAL,"LFP_data_img_wise","global_params",'meta_data','LFP_META','-v7.3')

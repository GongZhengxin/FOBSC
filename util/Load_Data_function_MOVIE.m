function Load_Data_function_MOVIE(data_path)

cd(data_path)
clear
mkdir processed
%% Load Data
% Load NI Data
SGLX_Folder = dir('NPX*');
session_name = SGLX_Folder(1).name;
g_number = session_name(end);
NIFileName=fullfile(session_name, sprintf('%s_t0.nidq', session_name));
[NI_META, AIN, DCode_NI] = load_NI_data(NIFileName);

% Load ML Data
ML_FILE = dir('*bhv2');
ml_name = ML_FILE(1).name;
[exp_day, exp_subject] = parsing_ML_name(ml_name);

% Load Grid

textData = fileread('GRID.txt');
lines = strsplit(textData, '\n');
Grid = lines{1}(1:end-1);
Notes = lines{2};
trial_ML_name = fullfile('processed',sprintf('ML_%s.mat',ml_name(1:end-5)));
file_exist = length(dir(trial_ML_name));
if(file_exist)
    load(trial_ML_name);
else
    trial_ML = mlread(ml_name);
    save(trial_ML_name, "trial_ML")
end


ImecFileName=fullfile(session_name,sprintf('%s_imec0',session_name), sprintf('%s_t0.imec0.lf',session_name));
[IMEC_META, DCode_IMEC] = load_IMEC_data(ImecFileName);
ImecFileName=fullfile(session_name,sprintf('%s_imec0',session_name), sprintf('%s_t0.imec0.ap',session_name));
IMEC_AP_META = load_meta(sprintf('%s.meta', ImecFileName));



% Do Sync between Devices
SyncLine = examine_and_fix_sync(DCode_NI, DCode_IMEC);


%% check for alignment between ML and NI
onset_times = 0;
offset_times = 0;
onset_times_by_trial_ML = zeros([1, length(trial_ML)]);
for tt = 1:length(trial_ML)
    onset_times_by_trial_ML(tt) = sum(trial_ML(tt).BehavioralCodes.CodeNumbers==64);
    onset_times = onset_times + onset_times_by_trial_ML(tt);
    offset_times = offset_times + sum(trial_ML(tt).BehavioralCodes.CodeNumbers==32);
end
fprintf('MonkeyLogic Has\n%d trials \n%d onset \n%d offset \n', length(trial_ML), onset_times, offset_times)

%% check for eye
trial_valid_idx = zeros([1, onset_times])
onset_marker = 0;
for trial_idx = 1:length(trial_ML)
    if(any(trial_ML(trial_idx).BehavioralCodes.CodeNumbers==64))
        onset_marker = onset_marker +1;
        if(~trial_ML(trial_idx).TrialError)
            trial_valid_idx(onset_marker) = trial_ML(trial_idx).Condition;
        end
    end
end
%% Look Up For Real Onset Time
before_onset_measure = 200;
after_onset_measure = 200;
after_onset_stats = 300;

onset_LOC = find(DCode_NI.CodeVal==64);
onset_times = length(onset_LOC);
po_dis = zeros([onset_times, 1+before_onset_measure+after_onset_stats]);
onset_time_ms = zeros([1, onset_times]);
for tt = 1:onset_times
    onset_time_ms(tt) = floor(DCode_NI.CodeTime(onset_LOC(tt)));
    po_dis(tt,:) = AIN(onset_time_ms(tt)-before_onset_measure:onset_time_ms(tt)+after_onset_stats);
end

subplot(1,5,2)
shadedErrorBar((1:size(po_dis,2))-before_onset_measure,mean(po_dis),std(po_dis))
hold on
baseline = mean(mean(po_dis(:,1:before_onset_measure)));
hignline = mean(mean(po_dis(:,before_onset_measure+(after_onset_measure:before_onset_measure+100)),"omitnan"),"omitnan");
thres = 0.5*baseline + 0.5*hignline;
yline(thres)
xlabel('time from event');title('Before time calibration')


onset_latency = zeros([1, size(po_dis,1)]);
for tt = 1:size(po_dis,1)
    onset_latency(tt) = find(po_dis(tt,:)>thres,1)-before_onset_measure;
%     onset_time_ms(tt) = onset_time_ms(tt) + onset_latency(tt);
onset_time_ms(tt) = onset_time_ms(tt);
end
subplot(1,5,5); hist(onset_latency,20);
xlabel('Latency ms')
xline(min(onset_latency),'LineWidth',2); xline(max(onset_latency),'LineWidth',2)

subplot(1,5,3)
po_dis = zeros([onset_times, 1+before_onset_measure+after_onset_stats]);
for tt = 1:onset_times
    po_dis(tt,:) = AIN(onset_time_ms(tt)-before_onset_measure:onset_time_ms(tt)+after_onset_stats);
end
shadedErrorBar((1:size(po_dis,2))-before_onset_measure,mean(po_dis),std(po_dis))
xlabel('time from event'); title('After time calibration')

subplot(1,5,4)
po_dis = zeros([onset_times, 1+before_onset_measure+after_onset_stats]);
for tt = 1:onset_times
    if(trial_valid_idx(tt))
        po_dis(tt,:) = AIN(onset_time_ms(tt)-before_onset_measure:onset_time_ms(tt)+after_onset_stats);
    end
end
po_dis(~trial_valid_idx,:)=[];
shadedErrorBar((1:size(po_dis,2))-before_onset_measure,mean(po_dis),std(po_dis))
xlabel('time from event'); title('Exclude Non-Look Trial')
saveas(gcf,'processed\Prep_sync_ni_ml')
% Transform about Data

%%
figure
img_size = max(trial_valid_idx);
onset_t = [];
for img = 1:img_size
    onset_t(img) = sum(trial_valid_idx==img);
end
plot(1:img_size,onset_t)
xlim([1,img_size])
ylim([0, max(onset_t)+1])
saveas(gcf,'processed\Prep_img_size')
%%

save_name = fullfile('processed',sprintf('META_%s_%s_%s.mat', exp_day, exp_subject, 'movie270'));
save(save_name, "Grid",'Notes',"ml_name","trial_valid_idx", "onset_time_ms", "NI_META", "AIN", "DCode_NI", "IMEC_META","DCode_IMEC","SyncLine","IMEC_AP_META","img_size","g_number");
end
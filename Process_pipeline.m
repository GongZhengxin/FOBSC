
cd 'E:\ProcessPipeline_LYP'
addpath(genpath('C:\Users\admin\AppData\Roaming\MathWorks\MATLAB Add-Ons\Apps\NIMHMonkeyLogic22'))
addpath(genpath("util\"))

interested_path={'E:\241029_word_ses2'};

nas_location = 'Z:\Monkey_ephys\NPX_Processed';
nas_location_raster = 'Z:\Monkey_ephys\NPXRaster_Pool';
LocalData = 'D:\CookedData';
for path_now = 1:length(interested_path) 
    Load_Data_function(interested_path{path_now});
    PostProcess_function_raw(interested_path{path_now}, nas_location_raster);
    PostProcess_function(interested_path{path_now}, nas_location);
    PostProcess_function_LFP(interested_path{path_now});
    fileName = dir(fullfile(interested_path{path_now},"processed",'GoodUnit_2*'));
    Destination_file = fullfile(LocalData, fileName.name(10:end-4));
    mkdir(Destination_file)
    copyfile(fullfile(interested_path{path_now},"processed"), Destination_file)
    close all
end


% %%
% clear a b c
% all_data = dir(fullfile(LocalData,'2*'));
% for path_now = 1:length(all_data)
%     GU_name = all_data(path_now).name;
%     split = find(GU_name=='_');
%     a{path_now} = GU_name(1:split(1)-1);
%     b{path_now} = GU_name(split(1)+1:split(2)-1);
%     c{path_now} = GU_name(split(2)+1:end-3);
%     d{path_now} = length(load(fullfile(LocalData,GU_name,dir(fullfile(LocalData,GU_name,"META*")).name)).onset_time_ms);
%     e{path_now} = load(fullfile(LocalData,GU_name,dir(fullfile(LocalData,GU_name,"META*")).name)).Grid;
%     f{path_now} = load(fullfile(LocalData,GU_name,dir(fullfile(LocalData,GU_name,"META*")).name)).Notes;
%     h{path_now} = length(load(fullfile(LocalData,GU_name,dir(fullfile(LocalData,GU_name,"GoodUnit_2*")).name)).GoodUnitStrc);
%     fprintf('%d %d\n', path_now, length(all_data))
% end
% x = table(a',b',c',e',d',h',f','VariableNames',{'Day','Subject','Image','Gird','OnsetTimes','#Neuron','Notes'});
% writetable(x,fullfile(LocalData, 'Summary.xls'))
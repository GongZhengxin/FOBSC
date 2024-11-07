function log_message(log_file_path, message)
    % LOG_MESSAGE - 控制日志写入函数（实时打开和关闭文件）
    %   log_message(log_file_path, message) - 将信息写入指定的日志文件中
    %   log_message(log_file_path, 'start') - 开启日志记录的提示信息
    %   log_message(log_file_path, 'stop') - 停止日志记录的提示信息
    disp(message);
    if nargin ~= 2
        error('必须传入日志文件路径和消息文本。');
    end

    if strcmp(message, 'start')
        % 启动日志记录提示
        fprintf('日志记录已开启。');
        log_message(log_file_path, '日志记录已开启');
        return;
    elseif strcmp(message, 'stop')
        % 停止日志记录提示
        log_message(log_file_path, '日志记录已关闭');
        fprintf('日志记录已关闭。');
        return;
    else
        % 写入日志信息
        try
            % 获取调用者信息
            stack = dbstack;
            if numel(stack) > 1
                caller_name = stack(2).name; % 获取直接调用者的名称
            else
                caller_name = 'Command Window'; % 直接从命令窗口调用
            end

            % 获取当前时间
            current_time = datetime('now', 'Format', 'MM-dd HH:mm:ss');

            % 打开日志文件，以追加模式写入
            log_file = fopen(log_file_path, 'a');
            if log_file == -1
                error('无法打开日志文件：%s', log_file_path);
            end

            % 写入日志信息
            fprintf(log_file, '[%s](%s)>> %s', current_time, caller_name, message);

            % 关闭日志文件
            fclose(log_file);
        catch ME
            fprintf('日志写入时发生错误：%s', ME.message);
        end
    end
end

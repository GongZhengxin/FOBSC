function SyncLine = examine_and_fix_sync(DCode_NI, DCode_IMEC, logfile)

if nargin < 3
    logfile = fopen(sprintf('%s_Proc.log', mfilename), 'w');
end
se = find(DCode_NI.CodeVal==1);
SyncLine.NI_time =  DCode_NI.CodeTime(se);
SyncLine.imec_time =  DCode_IMEC.CodeTime;
log_message(logfile, sprintf('Syncing...\n'))
log_message(logfile, sprintf('NI has %d edges while IMEC has %d\n', length(SyncLine.NI_time), length(SyncLine.imec_time)))

d1 = diff(SyncLine.imec_time);
d1 = d1(2:end);
d2 = diff(SyncLine.NI_time);
d2 = d2(2:end);
fig = figure();
nexttile
plot(d1);ylim([950,2000])
title(sprintf('IMEC max diff is %f', max(d1)))
nexttile
plot(d2);ylim([950,2000])
title(sprintf('NI max diff is %f', max(d2)))
xlabel('# of rising edge')
ylabel('time lag between edges')


if (length(SyncLine.NI_time)~=length(SyncLine.imec_time))
    warning('Sync Fail! Fixing...\n')
    index = find(d2 > 1200);

    if ~isempty(index)
        for i = 1:length(index)
            idx = index(i)+i;
            new_value = (SyncLine.NI_time(idx) + SyncLine.NI_time(idx + 1)) / 2;
            SyncLine.NI_time = [SyncLine.NI_time(1:idx), new_value, SyncLine.NI_time(idx+1:end)];
        end
    end
    d1 = diff(SyncLine.imec_time);
    d1 = d1(2:end);
    d2 = diff(SyncLine.NI_time);
    d2 = d2(2:end);
    nexttile
    plot(d1);ylim([950,2000])
    title(sprintf('IMEC max diff is %f', max(d1)))
    nexttile
    plot(d2);ylim([950,2000])
    title(sprintf('NI max diff is %f', max(d2)))
    xlabel('# of rising edge')
    ylabel('time lag between edges')


else
    log_message(logfile, sprintf('Sync Success!\n'))
end


if(strcmpi(pwd,'E:\240925\FoodBigData'))
    terr = zeros([1,length(SyncLine.NI_time)]);
    loc = find(diff(SyncLine.NI_time)<800);
    SyncLine.NI_time(loc(2))=[];
end
for ii = 1:length(SyncLine.NI_time)
    terr(ii)=SyncLine.NI_time(ii)-SyncLine.imec_time(ii);
end
nexttile
plot(terr)

print(fig, 'processed\Sync.svg', '-dsvg');
close(fig)

if nargin < 2
    fclose(logfile);
    delete(logfile);
end
end
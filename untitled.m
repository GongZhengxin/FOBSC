% load processed\GoodUnit_241001_Facai_WordLocalizer_g0.mat
dp1 = [];
dp2 = [];
rm = [];
for gg = 1:length(GoodUnitStrc)
    d1 = mean(GoodUnitStrc(gg).response_matrix_img([61:120, 151:180], global_params.pre_onset+(80:200)),2);
    d2 = mean(GoodUnitStrc(gg).response_matrix_img([1:60,121:150], global_params.pre_onset+(80:200)),2);
    dp1(gg) = (mean(d1)-mean(d2)) ./ sqrt(0.5*(std(d1)^2+std(d2)^2));
    d1 = mean(GoodUnitStrc(gg).response_matrix_img([91:120], global_params.pre_onset+(80:200)),2);
    d2 = mean(GoodUnitStrc(gg).response_matrix_img([1:60,121:150], global_params.pre_onset+(80:200)),2);
    dp2(gg) = (mean(d1)-mean(d2)) ./ sqrt(0.5*(std(d1)^2+std(d2)^2));
%     dp1(gg) = (mean(d1)-mean(d2))/(mean(d1)+mean(d2))
    rm =[rm, zscore(mean(GoodUnitStrc(gg).response_matrix_img(:, global_params.pre_onset+(70:200)),2))];
end
% 
sum(dp1>0.5)

figure; 
[a,b] = sort(dp1,'descend');
hist(a)
figure; 
subplot(1,2,1)
imagesc(rm(:, :)')
clim([-1.5,1.5])
% colormap('jet')

subplot(1,2,2); hold on
plot(a,length(GoodUnitStrc):-1:1,'LineWidth',2)
xline(0.2,'LineWidth',2)
xline(-0.2, 'LineWidth',2)
ylim([1, length(GoodUnitStrc)])
ylabel('# Unit')
xlabel('Body Selectivity')
for gg = 1:length(GoodUnitStrc)
    pos(gg)=GoodUnitStrc(gg).spikepos(2);
end
sum(dp1>0.2)
figure; hold on

    scatter(pos, dp1,6,'b','filled')
    scatter(pos, dp2,6,'r','filled')

xlabel('Distance To Tip')
ylabel('Food Selectivity')
md = polyfit(pos,dp1,1);
x1 = [0:1:2000];
y1 = polyval(md,x1);
plot(x1,y1,'LineWidth',3)

%
figure
for uu = 1:length(a)
    pp=[];
    for cc = 1:3
        switch cc
            case 1
                interested_data = 17:32;
            case 2
                 interested_data = 1:16;
            case 3
                 interested_data = 33:96;
        end
        pp(cc,:) = mean(GoodUnitStrc(b(uu)).response_matrix_img(interested_data,:));
    end
    plot(global_params.PsthRange, pp,LineWidth=2);
    legend('F','B','O')
    pause
end
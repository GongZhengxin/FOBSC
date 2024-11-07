function r = give_me_nc(raster, img_idx, intested_img)
boot_times = 2;
r = zeros([1, boot_times]);
for bb = 1:boot_times
    d1 = zeros([1,length(intested_img)]);
    d2 = d1;
    for ii = 1:length(intested_img)
        img_now = intested_img(ii);
        loc = find(img_idx==img_now);
        data_length = length(loc);
        oo = randperm(data_length);
        d1(ii) = mean(raster(loc(oo(1:floor(data_length/2)))));
        d2(ii) = mean(raster(loc(oo(floor(data_length/2)+1:end))));
    end
    r(bb)=corr(d1',d2');
end
r = mean(r);
r = (2*r)/(1+r);
end
function r = lscov_r(feature, response)



cv = cvpartition(length(response), 'KFold', 4);

% 初始化存储R值的变量
R_values = zeros(cv.NumTestSets, 1);

for fold = 1:cv.NumTestSets

    trainIdx = training(cv, fold);
    testIdx = test(cv, fold);

    fc6_train = feature(trainIdx, :);
    response_train = response(trainIdx);
    

    fc6_test = feature(testIdx, :);
    response_test = response(testIdx);
    
    % 进行线性回归
    [beta, stdx, ~] = lscov([fc6_train, ones(size(fc6_train, 1), 1)], response_train);
    
    % 预测测试集
    predictions = [fc6_test, ones(size(fc6_test, 1), 1)] * beta;
    
    % 计算预测R值
    R = corr(response_test, predictions);
    R_values(fold) = R;
end
r = mean(R_values);
end
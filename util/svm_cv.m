function acc = svm_cv(response_matrix, labels)
cv = cvpartition(labels, 'KFold', 8); % 10-fold cross-validation
svmModel = fitcsvm(response_matrix', labels, 'KernelFunction', 'linear', 'Standardize', true, 'CVPartition', cv);
predictions = kfoldPredict(svmModel);
acc = sum(predictions == labels') / length(labels);
end
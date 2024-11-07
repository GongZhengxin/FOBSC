function cosine_similarity = calculate_cosine_similarity(vector1, vector2)
    dot_product = dot(vector1, vector2);
    norm_vector1 = norm(vector1);
    norm_vector2 = norm(vector2);
    cosine_similarity = dot_product / (norm_vector1 * norm_vector2);
end

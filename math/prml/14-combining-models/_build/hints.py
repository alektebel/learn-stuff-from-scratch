"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from the combining-models module (Bishop's chapter 14) is
listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The purity helpers (`_impurity`, `_majority`), the demo and
its data builders are left implemented: they are infrastructure the exercise
stands on, not the learners themselves.

Regenerate the template with:

    python3 .claude/skills/graded-module/scripts/make_templates.py \\
        math/prml/14-combining-models math/prml/14-combining-models/_build/hints.py
"""

HINTS = {
 "combine.py": {
  "gini":
      "Gini impurity of a group: 1 - sum_c p_c^2, where p_c is the fraction of the "
      "group in class c. It is the default split criterion.",
  "entropy":
      "Shannon entropy -sum_c p_c log2 p_c in bits; skip classes with p = 0 so you "
      "never take log(0). A second, interchangeable impurity measure.",
  "best_split":
      "Try every feature and every midpoint between consecutive distinct values. "
      "Score a cut by the WEIGHTED child impurity (W_left * imp_left + W_right * "
      "imp_right) / W_total; plain counts are wrong whenever sample weights are "
      "passed. Return (feature, threshold, score) for the minimum, or None if no "
      "cut leaves min_leaf points on each side.",
  "fit_tree":
      "Recursive CART. At each node take the (weighted) majority label, stop on "
      "depth 0, a pure node, or no valid split, otherwise split on best_split and "
      "recurse on the two partitions. Return the nested dict {feature, threshold, "
      "left, right, label}.",
  "predict_tree":
      "Walk from the root: while feature is not None, go left when x[feature] <= "
      "threshold and right otherwise; return the leaf's label.",
  "decision_stump":
      "Depth-1 AdaBoost learner. For every feature and midpoint cut, label each "
      "side with its WEIGHTED majority and score the weighted fraction "
      "misclassified. Return (stump, error); a stump is {feature, threshold, left, "
      "right, label} with constant labels in the leaves. A good stump has error < "
      "0.5.",
  "predict_stump":
      "Apply a stump like a one-level tree: leaf if feature is None, otherwise "
      "left when x[feature] <= threshold and right otherwise.",
  "adaboost":
      "Discrete AdaBoost. Start with uniform weights; each round take the best "
      "stump (error eps), set alpha = 0.5 ln((1 - eps)/eps), multiply "
      "w_i *= exp(-alpha y_i h_t(x_i)) with targets y in {+1,-1}, and RENORMALISE "
      "the weights. Record the combined classifier's training error, the product "
      "bound prod 2 sqrt(eps(1-eps)) and exp(-2 sum gamma^2), gamma = 1/2 - eps.",
  "adaboost_predict":
      "Combined vote: predict 1 when sum_t alpha_t h_t(x) >= 0, else 0.",
  "bagging":
      "For each of n_models draw n indices WITH replacement (rng.randrange), fit a "
      "tree on the bootstrap sample, then return (models, train_error). Uniform "
      "resampling without replacement would make every tree identical and defeat "
      "the variance reduction.",
  "bagging_predict":
      "Majority vote of the ensemble on one point: 1 when more than half the trees "
      "predict 1, else 0.",
 },
}

"""Reusable, schema-driven feature transformers.

Each transformer follows a scikit-learn-like ``fit``/``transform`` contract
and records ``feature_names_`` so training and inference always agree on the
feature space. Preprocessing lives here once and is reused by every trainer
and by the prediction engine — never duplicated.
"""

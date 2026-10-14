"""Explicit target eligibility; censoring never becomes a zero duration."""


def creation_masks(label):
    eligible = label["eligible"] and label["status"] != "cancelled"
    return {
        "classification": eligible and label["late"] is not None,
        "delay_regression": eligible
        and label["status"] == "reached"
        and label["late"] is True
        and label["delay_minutes"] is not None,
        "censored": eligible and label["quota_censored"],
    }


def rolling_masks(target):
    eligible = target["eligible"]
    return {
        "classification": eligible
        and target["target_kind"] == "delay_if_late"
        and target["late"] is not None,
        "duration_regression": eligible and target["target_minutes"] is not None,
        "censored": eligible and target["quota_censored"],
    }

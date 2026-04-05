"""
Adjudicator — previously determined finding status based on observation confidence.

With the removal of confidence scores (TwelveLabs does not provide them), the
adjudication step is no longer needed. If TwelveLabs flags an observation and
the policy resolver matches it to a finding type, it is treated as a finding.
Cleared patterns (e.g. drop + discard) are still handled by the policy resolver.
"""

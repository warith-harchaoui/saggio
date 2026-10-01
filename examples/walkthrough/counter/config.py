"""What a full run of this toy workload does.

``num_samples`` is one of the keys the audit reads to learn how much work a full
run performs, which is what lets it project from a measured slice to the whole.

It is four hundred thousand rather than five thousand for one reason, and the
reason is worth recording: a scaling series cuts the whole run into three slices
a factor of four apart, and at a thousandth of five thousand those three sizes
round to two. The workload was too small to demonstrate a thing the tool can do.
A full run here is still under a minute; the slices the audit actually takes are
a fraction of a second each.
"""

num_samples = 400_000

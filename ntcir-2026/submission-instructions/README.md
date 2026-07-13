# Run Submission Guidelines for the NTCIR 2026 Tip-of-the-Tongue (ToT) Shared Task

## Prerequisites
You must be [registered](https://research.nii.ac.jp/ntcir/ntcir-19/howto.html) to participate in the NTCIR 2026 Tip-of-the-Tongue (ToT) shared task.
The deadline for registration was **July 1**.

Please **create a new account** on [TIRA](https://www.tira.io/) by clicking on "Sign Up", or "Log In" if you already have an account.

## Upload Runs to NTCIR-ToT in TIRA

Please go to the [submission page](https://www.tira.io/task-overview/ntcir-tot) and click on "SUBMIT" and then on "UPLOAD NEW RUN".
Next, please fill out the runs details in the submission form that should look like the following:

<img width="1573" height="933" alt="Screenshot_20260713_111021" src="https://github.com/user-attachments/assets/5da52fe0-d9cd-4f8e-a312-174f873c8e1c" />


After you hit "NEXT", please upload your run file.
All submissions must be gzip-compressed run files (e.g., a file `run.txt.gz`.)
A sample runfile format is shown below. White space is used to separate columns. The width of the columns in the format is not important, but it is important to have exactly six columns per line with at least one space between the columns.

```text
1 Q0 pid1    1 2.73 runid1
1 Q0 pid2    2 2.71 runid1
1 Q0 pid3    3 2.61 runid1
1 Q0 pid4    4 2.05 runid1
1 Q0 pid5    5 1.89 runid1
```

Where:
* The first column is the query (topic) ID.
* The second column is currently unused and should always be "Q0".
* The third column is the official identifier of the retrieved document.
* The fourth column is the rank the document is retrieved.
* The fifth column is the score (integer or floating point) that generated the ranking. This score must be in descending (non-increasing) order.
* The sixth column is the ID of the run you are submitting.

After you have uploaded your run, it will appear under "Your Uploaded Runs".

Deadline for run submissions is **July 30**.
Please see the [task guidelines](https://ntcir-tot.github.io/guidelines) for additional information (e.g., links to datasets).
Please email ntcir-tot-organizers (at) googlegroups.com, if you have any questions.

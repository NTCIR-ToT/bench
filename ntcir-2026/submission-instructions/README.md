# Run Submission Guidelines for the Tip-of-my-Tongue shared task at NTCIR

<details>
<summary>Prerequisite: Register to the TOT task at NTCIR. Create an Account at TIRA.io and register a team to NTCIR-ToT in TIRA</summary>

We assume that you already [registered to the ToT shared task](https://research.nii.ac.jp/ntcir/ntcir-19/howto.html) at NTCIR (the registration is already closed).

Please create an account at TIRA (which we use . Please go to [https://www.tira.io/](https://www.tira.io/) and click on "Sign Up" to create a new account or "Log In" if you already have an account.

<img width="1042" height="965" alt="Screenshot_20251210_074005" src="https://github.com/user-attachments/assets/6f05d18d-3b03-4314-94b4-b1136613b362" />

</details>

## Upload Runs to NTCIR-ToT in TIRA


<details>
<summary>Step 0: Requirements</summary>

All submissions must be gzip-compressed run files. (e.g., a file `run.txt.gz`.)
</details>



<details>
<summary>Step 1: Upload Your Run</summary>

After you registered your team, you can go to the submission page [https://www.tira.io/task-overview/ntcir-tot](https://www.tira.io/task-overview/ntcir-tot) and click on "Submit" and then on "Upload new Run". A form like below will show where we ask a few questions on your run:

<img width="3054" height="1642" alt="Screenshot_20260709_212455" src="https://github.com/user-attachments/assets/ebf61fca-224d-4a07-8d61-8b13e77bf3b5" />

When you have filled out the questions, you can upload your run. The upload form directly checks if the uploaded run is syntactically valid and only accepts valid run files.

</details>




<details>
<summary>Step 2: Feedback by Organizers</summary>

After you have uploaded your run, it will appear under "Your Uploaded Runs". We make (additionally to the checks that the run file is syntactically valid that happen automatically during the upload) a manual review. The evaluation scores will remain blinded until the submission deadline is over. During the review of the run, we will look at its evaluation scores, and in case there seems to be an error (e.g., queries without retrieved documents, or very low effectiveness scores), we will give you feedback that you can look into the potential problem (we will not reveal the evaluation score, we will only give lightweight feedback such as "looks ok" or "there seems to be an error, please have a look").

The review is manually, and we do it usually within a day, if everything looks good, the "Your Uploaded Runs" entry will look like:

<img width="2976" height="345" alt="Screenshot_20260709_212810" src="https://github.com/user-attachments/assets/71a9f9fd-7ffe-4402-86a2-38034407a466" />


</details>


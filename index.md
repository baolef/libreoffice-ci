## About project
LibreOffice is a large and complex office software and has an extensive CI system to ensure that new patches do not introduce bugs. A lot of unit tests are run in Jenkins when contributers submit their patches to gerrit. It usually takes hours to run all the tests across different platforms, especially in rush hours. Therefore, a better test selection method is needed to reduce the load in testing while maintaining a high software quality.

Recently, machine learning is used to predict whether a patch can pass a given test. This can greatly reduce the testing load because we can skip the tests that is very likely to pass when a patch is submitted. Therefore, a machine learning based unit test selection algorithm is implemented to select tests to run in the CI chain to reduce testing load.

The model is available on [Github](https://github.com/baolef/libreoffice-ci) and integrated in [Jenkins](https://ci.libreoffice.org/job/gerrit_master_ml/).

## Model performance

`testlabelselect` model predicts the failing probability of each unit test given the patch.

|               | Fail (Predicted) | Pass (Predicted) |
|---------------|------------------|------------------|
| Fail (Actual) | 3860             | 203              |
| Pass (Actual) | 191593           | 1109768          |

`testfailure` model predicts the overall failing probability of a patch based on patch features only.

|               | Fail (Predicted)  | Pass (Predicted) |
|---------------|-------------------|------------------|
| Fail (Actual) | 614               | 527              |
| Pass (Actual) | 2155              | 4863             |

`testoverall` model improves upon `testfailure` by using `testlabelselect` predictions to predict whether a patch will fail any unit test.

|               | Fail (Predicted) | Pass (Predicted) |
|---------------|------------------|------------------|
| Fail (Actual) | 810              | 331              |
| Pass (Actual) | 2413             | 4605             |

A smart inference is built based on `testlabelselect` and `testoverall` predictions. By setting a threshold for the number of failed unit tests, 91% of failures can be captured, while reducing computation by 57%.

|               | Fail (Predicted) | Pass (Predicted) |
|---------------|------------------|------------------|
| Fail (Actual) | 10617            | 1054             |
| Pass (Actual) | 30103            | 39815            |

Currently, the smart inference is integrated into [Jenkins](https://ci.libreoffice.org/job/gerrit_master_ml/) to save computation. If a patch is likely to fail any unit test, the sequential [fast track](https://ci.libreoffice.org/job/gerrit_master_seq/) will be run because it is assumed that the patch will fail some unit tests and there is no need to run everything. If it is likely to pass, the [normal track]((https://ci.libreoffice.org/job/gerrit_master/)) will be run to ensure code correctness.

`testlabelselect` is not directly used to select unit tests because it is not able to capture all failures, about 5% failures will escape and it could cause severe problem.

## Tasks
- [x] [Join #tdf-infra](_posts/2023-05-31-week1.md#join-tdf-infra)
- [ ] Investigate how to select tests in Jenkins
- [x] [Familiar with Mozilla's work](_posts/2023-05-31-week1.md#familiar-with-mozillas-work)
- [x] [Commit feature extraction](_posts/2023-06-07-week2.md#commit-feature-extraction)
- [x] [Unit test feature extraction](_posts/2023-06-07-week2.md#unit-test-feature-extraction)
- [x] [Model training](_posts/2023-06-22-week4.md#model-training)
- [x] [Model inference](_posts/2023-06-29-week5.md#model-inference)
- [x] [Model sharing](_posts/2023-06-29-week5.md#model-sharing)
- [x] [Jenkins integration](_posts/2023-08-03-week10.md#jenkins-integration)
- [x] [Result archive](_posts/2023-07-20-week8.md#result-archive)
- [x] [Model improvement](_posts/2023-07-27-week9.md#model-improvement)
- [x] [Smart inference](_posts/2023-08-03-week10.md#smart-inference)

## My Work during GSoC
During the 3-month GSoC program, I trained 3 XGBoost models (`testlabelselect`, `testfailure`, `testoverall`) to select unit tests for a patch to run, and integrated the models in Jenkins.

In the first month, I trained `testlabelselect` to predict whether `patch` will fail `test` by feeding `(patch,test)` pair into the model, which predicts a value between 0 (pass) and 1 (fail). The first version of `testlabelselect` is able to capture 90% of fail unit tests , while skipping 80% of pass unit tests.

In the second month, I improved the performance of `testlabelselect` from 90% fail recall and 80% pass recall to **95%** fail recall and **85%** pass recall by manipulating the feature extraction pipelines. I've also trained `testfailure` to predict whether `patch` will fail any unit tests solely based on `patch` features for Jenkins integration purpose. However, its performance (54% fail recall and 69% pass recall) is far worse than `testlabelselect`.

In the third month, I trained a new model `testoverall`, an improvement of `testfailure`, that uses `testlabelselect` prediction results to predict whether `patch` will fail any unit test. The model itself achieves a 71% fail recall and 66% pass recall. With smart inference algorithm, the performance is improved to **91%** fail recall and **57%** pass recall.

## What's next
Since this project is something from 0 to 1, there is space for future development:
- Model improvement
- Jenkins job improvement when the model reaches a better performance

## Acknowledgement

I'm honored that I can be chosen by LibreOffice to be part of GSoC 2023 program. I'm also glad that most goals are achieved during the project period.

I'd like to thank Thorsten Behrens, Christian Lohmaier and Stéphane Guillou, who have been very helpful to my project.

I also want to thank the LibreOffice community who has been providing me a lot of feedbacks throughout the project.

At last, I'd like to thank Mozilla's [bugbug](https://github.com/mozilla/bugbug) and [rust-code-analysis](https://mozilla.github.io/rust-code-analysis/), whose work provides me a code base to work on.

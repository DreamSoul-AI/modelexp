# RPipe
Research Pipeline
 
## Requirements
See `requirements.txt`

## Instructions
- Use `make.sh` to generate run script
- Use `make.py` to generate exp script
- Use `process.py` to process exp results
- Hyperparameters can be found in `config.yml` and `process_control()` in `module/hyper.py`

## Examples
 - Generate run script
    ```ruby
    bash make.sh
    ```
 - Generate run script
    ```ruby
    python make.py --mode base
    ```
 - Train with MNIST and linear model
    ```ruby
    python train_model.py --control_name MNIST_linear
    ```
 - Test with CIFAR10 and resnet18 model
    ```ruby
    python test_model.py --control_name CIFAR10_resnet18
    ```
 - Process exp results
    ```ruby
    python process.py
    ```

## Results
- Learning curves of MNIST
<p align="center">
<img src="/asset/MNIST_Accuracy_mean.png">
</p>


- Learning curves of CIFAR10
<p align="center">
<img src="/asset/CIFAR10_Accuracy_mean.png">
</p>


## Acknowledgements
*Enmao Diao*

## Model 资料与评测维护（gyd）

此分支在原训练流程之外提供三个独立任务：Grokbot CSV 增量同步、只读字段/一致性校验、语言模型代码/Agent/数学评分维护。Markdown 由 Grokbot 管理，专项和基座单列；不生成正文、研究队列或每日摘要。

- [使用指南](skills/model-research/README.md)与[Skill](skills/model-research/SKILL.md)
- [文档导航](docs/README.md)与[项目约定](REPO.md)
- [服务器部署与验收](skills/model-research/references/server-deployment.md)

真实配置、状态、资料和凭据均放仓外。历史方案及报告快照已从当前树清理，可通过 Git 和私有归档查阅。

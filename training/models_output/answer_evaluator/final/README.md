---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- dense
- generated_from_trainer
- dataset_size:21250
- loss:CosineSimilarityLoss
base_model: sentence-transformers/all-MiniLM-L6-v2
widget:
- source_sentence: How does this role fit into your career path? next step future
  sentences:
  - I'm always eager to learn and embrace change as a way to improve. For example,
    I once had to switch to a new tech stack and picked it up quickly. How do you
    stay updated with industry trends?
  - I'm always eager to learn and embrace change as a way to improve. For example,
    I once had to switch to a new tech stack and picked it up quickly. Tell me about
    a time you had to learn something completely new quickly.
  - My long-term goal is to grow into a senior role where I can contribute more strategically
    and mentor others. This role brings me closer to that. How does this role fit
    into your career path?
- source_sentence: How do you organize and prioritize your daily tasks? tool method
  sentences:
  - I follow a structured workflow and use tools like Jira/Trello/Notion to manage
    my tasks efficiently. What tools or methods help you stay organized?
  - I'm motivated by challenges and the opportunity to grow both personally and professionally.
    What motivates you to come to work every day?
  - I follow a structured workflow and use tools like Jira/Trello/Notion to manage
    my tasks efficiently. How do you organize and prioritize your daily tasks?
- source_sentence: Describe your ideal workday. tool method
  sentences:
  - My long-term goal is to grow into a senior role where I can contribute more strategically
    and mentor others. This role brings me closer to that. Where do you see yourself
    in 5 years?
  - I'm always eager to learn and embrace change as a way to improve. For example,
    I once had to switch to a new tech stack and picked it up quickly. Describe a
    time you failed and what you learned from it.
  - I follow a structured workflow and use tools like Jira/Trello/Notion to manage
    my tasks efficiently. Describe your ideal workday.
- source_sentence: Why do you want to work at our company? goal drive
  sentences:
  - I'm motivated by challenges and the opportunity to grow both personally and professionally.
    Why do you want to work at our company?
  - My long-term goal is to grow into a senior role where I can contribute more strategically
    and mentor others. This role brings me closer to that. What kind of growth opportunities
    are you looking for?
  - I believe communication and mutual respect are key to successful collaboration.
    In one project, we achieved X because of great teamwork. How do you build trust
    with new teammates?
- source_sentence: Describe a project where teamwork was essential to success. collaboration
    cooperate
  sentences:
  - I'm motivated by challenges and the opportunity to grow both personally and professionally.
    Why do you want to work at our company?
  - I'm motivated by challenges and the opportunity to grow both personally and professionally.
    How do you stay motivated during repetitive tasks?
  - I believe communication and mutual respect are key to successful collaboration.
    In one project, we achieved X because of great teamwork. Describe a project where
    teamwork was essential to success.
pipeline_tag: sentence-similarity
library_name: sentence-transformers
metrics:
- pearson_cosine
- spearman_cosine
model-index:
- name: SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2
  results:
  - task:
      type: semantic-similarity
      name: Semantic Similarity
    dataset:
      name: interview val
      type: interview-val
    metrics:
    - type: pearson_cosine
      value: 0.6978723611969696
      name: Pearson Cosine
    - type: spearman_cosine
      value: 0.5242777266097143
      name: Spearman Cosine
---

# SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It maps sentences & paragraphs to a 384-dimensional dense vector space and can be used for semantic textual similarity, semantic search, paraphrase mining, classification, clustering, and more.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) <!-- at revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 -->
- **Maximum Sequence Length:** 256 tokens
- **Output Dimensionality:** 384 dimensions
- **Similarity Function:** Cosine Similarity
- **Supported Modality:** Text
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'transformer_task': 'feature-extraction', 'modality_config': {'text': {'method': 'forward', 'method_output_name': 'last_hidden_state'}}, 'module_output_name': 'token_embeddings', 'architecture': 'BertModel'})
  (1): Pooling({'embedding_dimension': 384, 'pooling_mode': 'mean', 'include_prompt': True})
  (2): Normalize({})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```
Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    'Describe a project where teamwork was essential to success. collaboration cooperate',
    'I believe communication and mutual respect are key to successful collaboration. In one project, we achieved X because of great teamwork. Describe a project where teamwork was essential to success.',
    "I'm motivated by challenges and the opportunity to grow both personally and professionally. Why do you want to work at our company?",
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.9260, 0.7030],
#         [0.9260, 1.0000, 0.7549],
#         [0.7030, 0.7549, 1.0000]])
```
<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### Metrics

#### Semantic Similarity

* Dataset: `interview-val`
* Evaluated with [<code>EmbeddingSimilarityEvaluator</code>](https://sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.sentence_transformer.evaluation.EmbeddingSimilarityEvaluator)

| Metric              | Value      |
|:--------------------|:-----------|
| pearson_cosine      | 0.6979     |
| **spearman_cosine** | **0.5243** |

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 21,250 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 100 samples:
  |          | sentence_0                                                                          | sentence_1                                                                          | label                                                           |
  |:---------|:------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------|:----------------------------------------------------------------|
  | type     | string                                                                              | string                                                                              | float                                                           |
  | modality | text                                                                                | text                                                                                |                                                                 |
  | details  | <ul><li>min: 10 tokens</li><li>mean: 23.68 tokens</li><li>max: 109 tokens</li></ul> | <ul><li>min: 25 tokens</li><li>mean: 73.41 tokens</li><li>max: 229 tokens</li></ul> | <ul><li>min: 0.9</li><li>mean: 0.92</li><li>max: 0.96</li></ul> |
* Samples:
  | sentence_0                                                                                                                                                                                                                                                                         | sentence_1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | label                           |
  |:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------|
  | <code>Tell me about a time you had to learn something completely new quickly. adjust learn</code>                                                                                                                                                                                  | <code>I'm always eager to learn and embrace change as a way to improve. For example, I once had to switch to a new tech stack and picked it up quickly. Tell me about a time you had to learn something completely new quickly.</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | <code>0.9400000000000001</code> |
  | <code>How do you organize and prioritize your daily tasks? process daily routine</code>                                                                                                                                                                                            | <code>I follow a structured workflow and use tools like Jira/Trello/Notion to manage my tasks efficiently. How do you organize and prioritize your daily tasks?</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | <code>0.9400000000000001</code> |
  | <code>What is the primary mechanism by which cloud computing services achieve scalability, and how do the trade-offs between auto-scaling, load balancing, and queuing mechanisms impact the overall system resilience and performance? computer science devops methodology</code> | <code>Cloud computing services achieve scalability primarily through the use of virtualization and automation. Virtualization allows for the creation of virtual resources, such as servers, storage, and networks, which can be easily scaled up or down as needed. Automation, on the other hand, enables the dynamic allocation of these virtual resources in response to changes in demand, allowing for efficient and flexible scaling.<br><br>Auto-scaling, load balancing, and queuing mechanisms are three key techniques used to manage and optimize the scaling of cloud-based systems. Each of these mechanisms has its own trade-offs in terms of system resilience and performance:<br><br>1. Auto-scaling: This mechanism automatically adjusts the number of active instances (e.g., virtual machines) based on the current workload. Auto-scaling can help improve system resilience by automatically adding capacity to handle spikes in demand, but it can also introduce additional complexity and overhead, as instances need</code> | <code>0.96</code>               |
* Loss: [<code>CosineSimilarityLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#cosinesimilarityloss) with these parameters:
  ```json
  {
      "loss_fct": "torch.nn.modules.loss.MSELoss",
      "cos_score_transformation": "torch.nn.modules.linear.Identity"
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `per_device_train_batch_size`: 16
- `num_train_epochs`: 3
- `max_steps`: -1
- `learning_rate`: 5e-05
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_steps`: 0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `optim_target_modules`: None
- `gradient_accumulation_steps`: 1
- `average_tokens_across_devices`: True
- `max_grad_norm`: 1
- `label_smoothing_factor`: 0.0
- `bf16`: False
- `fp16`: False
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `use_cache`: False
- `neftune_noise_alpha`: None
- `torch_empty_cache_steps`: None
- `auto_find_batch_size`: False
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `include_num_input_tokens_seen`: no
- `log_level`: passive
- `log_level_replica`: warning
- `disable_tqdm`: False
- `project`: huggingface
- `trackio_space_id`: None
- `trackio_bucket_id`: None
- `trackio_static_space_id`: None
- `per_device_eval_batch_size`: 16
- `prediction_loss_only`: True
- `eval_on_start`: False
- `eval_do_concat_batches`: True
- `eval_use_gather_object`: False
- `eval_accumulation_steps`: None
- `include_for_metrics`: []
- `batch_eval_metrics`: False
- `save_only_model`: False
- `save_on_each_node`: False
- `enable_jit_checkpoint`: False
- `push_to_hub`: False
- `hub_private_repo`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_always_push`: False
- `hub_revision`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `restore_callback_states_from_checkpoint`: False
- `full_determinism`: False
- `seed`: 42
- `data_seed`: None
- `use_cpu`: False
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `dataloader_prefetch_factor`: None
- `dataloader_multiprocessing_context`: None
- `dataloader_in_order`: True
- `remove_unused_columns`: True
- `label_names`: None
- `train_sampling_strategy`: random
- `length_column_name`: length
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `ddp_static_graph`: None
- `ddp_backend`: None
- `ddp_timeout`: 1800
- `fsdp`: None
- `fsdp_config`: None
- `deepspeed`: None
- `debug`: []
- `skip_memory_metrics`: True
- `do_predict`: False
- `resume_from_checkpoint`: None
- `local_rank`: -1
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}
- `warmup_ratio`: None

</details>

### Training Logs
| Epoch  | Step | Training Loss | interview-val_spearman_cosine |
|:------:|:----:|:-------------:|:-----------------------------:|
| 0.1994 | 265  | -             | 0.1783                        |
| 0.3762 | 500  | 0.0033        | -                             |
| 0.3988 | 530  | -             | 0.4602                        |
| 0.5982 | 795  | -             | 0.4907                        |
| 0.7524 | 1000 | 0.0004        | -                             |
| 0.7976 | 1060 | -             | 0.5043                        |
| 0.9970 | 1325 | -             | 0.5031                        |
| 1.0    | 1329 | -             | 0.5037                        |
| 1.1287 | 1500 | 0.0004        | -                             |
| 1.1964 | 1590 | -             | 0.5172                        |
| 1.3958 | 1855 | -             | 0.5243                        |


### Training Time
- **Training**: 4.8 minutes

### Framework Versions
- Python: 3.13.15
- Sentence Transformers: 5.7.0
- Transformers: 5.18.0
- PyTorch: 2.11.0+cu130
- Accelerate: 1.15.0
- Datasets: 4.8.5
- Tokenizers: 0.23.2

## Additional Resources

- [Training and Finetuning Embedding Models with Sentence Transformers](https://huggingface.co/blog/train-sentence-transformers): the end-to-end guide for training or finetuning Sentence Transformer models.
- [Introduction to Matryoshka Embedding Models](https://huggingface.co/blog/matryoshka): variable-size embeddings that can be truncated with minimal quality loss.
- [Binary and Scalar Embedding Quantization for Significantly Faster & Cheaper Retrieval](https://huggingface.co/blog/embedding-quantization): post-training compression of embedding vectors.
- [Multimodal Embedding & Reranker Models with Sentence Transformers](https://huggingface.co/blog/multimodal-sentence-transformers): use text, image, audio, and video models through the same API.
- [Training and Finetuning Multimodal Embedding & Reranker Models with Sentence Transformers](https://huggingface.co/blog/train-multimodal-sentence-transformers): train multimodal embedding models, with a Visual Document Retrieval walkthrough.

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->
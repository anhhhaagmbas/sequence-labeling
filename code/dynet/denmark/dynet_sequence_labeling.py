from dynet_model import DynetModel
from helper import flatten, time
from extractor import read_conllu, read_bio
#from polyglot.embedding import Embedding

def validate_config(config):
    config_values = []
    if "task" not in config:
        config_values.append("task")
    if "language" not in config:
        config_values.append("language")
    if "embedding_type" not in config:
        config_values.append("embedding_type")
    elif "embedding" not in config and config["embedding_type"] != "self_trained":
        config_values.append("embedding")
#    else "embedding_dimensions" not in config:
#        config_values.append("embedding_dimensions")
    if "seeds" not in config:
        config_values.append("seeds")

    if len(config_values) > 0:
        raise ValueError(f"No value for {config_values} in config")

def read_data(config, data_type):
    root_path = "../../../data/"
    lang = config["language"]
    if config["task"] == "ner":
        return read_bio(root_path + f"ner/{lang}/{data_type}.bio")
    elif config["task"] == "pos":
        return read_conllu(root_path + f"pos/{lang}/{data_type}.conllu")

def configure_embedding(config):
    root_path = "../../../data/embeddings/"
    lang = config["language"]
    if config["embedding_type"] == "fasttext":
        raise NotImplemented("fasttext support missing")
    elif config["embedding_type"] == "polyglot":
        embedding = Embedding.load(root_path + "{lang}.tar.bz2")
        return embedding.vectors
    return None

def create_embedding_mapping(embedding):
    pass


def create_mapping(elements, default = None, embedding = None):
    if embedding: return create_embedding_mapping(embedding)

    elements = list(set(elements))
    elements.sort()
    if default: elements.insert(0, default)

    ele2int = {e:i for i, e in enumerate(elements)}
    return elements, ele2int

def evaluate(tagger, inputs, labels, tags):
    evaluation = {(t1, t2):0 for t1 in range(len(tags)) for t2 in range(len(tags))}
    predictions = [tagger.predict(i) for i in inputs]
    for s_preds, s_labs in zip(predictions, labels):
        for pred, label in zip(s_preds, s_labs):
            if pred != label: evaluation[(label, pred)] += 1
    return evaluation

def to_input(word, word2int, default):
    """
    Transforms words to their respective integer representation or unknown if not in dict
    """
    if word in word2int.keys():
        return word2int[word]
    return default 


def run_experiment(config):
    # Setup 
    validate_config(config)
    train_inputs, train_labels = read_data(config, "training")
    val_inputs, val_labels     = read_data(config, "validation")
    embedding                  = configure_embedding(config)

    int2tag, tag2int           = create_mapping(flatten(train_labels))
    int2word, word2int         = create_mapping(flatten(train_inputs), default = "<UNK>", embedding = embedding)

    train_inputs = [[word2int[w] for w in ws] for ws in train_inputs] 
    train_labels = [[tag2int[t] for t in ts] for ts in train_labels]

    val_inputs = [[to_input(w, word2int, word2int["<UNK>"]) for w in ws] for ws in val_inputs]
    val_labels = [[tag2int[t] for t in ts] for ts in val_labels]

    # Testing
    tagger = DynetModel(
                vocab_size = len(int2word),
                output_size = len(int2tag),
                embed_size = config["embedding_size"],
                hidden_size = config["hidden_size"],
                crf = config["crf"],
                seed = config["seed"])
    
    results, elapsed = time(tagger.fit, train_inputs, train_labels) 
    evaluation = evaluate(tagger, val_inputs, val_labels, int2tag)
    for expected, actual in evaluation.keys():
        key = (expected, actual)
        if evaluation[key] != 0:
            print(f"Expected {int2tag[expected]} - actual {int2tag[actual]} = {evaluation[key]} times")
    print(f"Training time {elapsed}")
    print(f"Training output {results}")

config = {
        "crf": False,
        "embedding_size": 86,
        "hidden_size": 100,
        "seed": 1, 
        "seeds": None,
        "task": "pos",
        "language": "da",
        "embedding_type": "self_trained",
        }

run_experiment(config)

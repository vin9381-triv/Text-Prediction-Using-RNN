import numpy as np
from nltk.tokenize import RegexpTokenizer
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Activation
from keras.optimizers import RMSprop
import pickle
import heapq

# Load and preprocess text data
path = '1661-0.txt'
text = open(path, encoding='utf-8').read().lower()
tokenizer = RegexpTokenizer(r'\w+')
words = tokenizer.tokenize(text)
unique_words = np.unique(words)
unique_word_index = dict((c, i) for i, c in enumerate(unique_words))

# Save unique_word_index to a file for later use
with open('unique_word_index.pkl', 'wb') as f:
    pickle.dump(unique_word_index, f)

WORD_LENGTH = 5
prev_words, next_words = [], []

for i in range(len(words) - WORD_LENGTH):
    prev_words.append(words[i:i + WORD_LENGTH])
    next_words.append(words[i + WORD_LENGTH])

X = np.zeros((len(prev_words), WORD_LENGTH, len(unique_words)), dtype=bool)
Y = np.zeros((len(next_words), len(unique_words)), dtype=bool)

for i, each_words in enumerate(prev_words):
    for j, each_word in enumerate(each_words):
        X[i, j, unique_word_index[each_word]] = 1
    Y[i, unique_word_index[next_words[i]]] = 1

# Model definition
#! Add one more hidden layer, regularization and drop out
model = Sequential()
model.add(LSTM(128, input_shape=(WORD_LENGTH, len(unique_words))))
model.add(Dense(len(unique_words)))
model.add(Activation('softmax'))

optimizer = RMSprop(learning_rate=0.01)
model.compile(loss='categorical_crossentropy', optimizer=optimizer, metrics=['accuracy'])

# Training and saving the model
history = model.fit(X, Y, validation_split=0.05, batch_size=128, epochs=25, shuffle=True).history
model.save('keras_next_word_model.h5')
pickle.dump(history, open("history.p", "wb"))

# Loading the model and unique_word_index for prediction
model = load_model('keras_next_word_model.h5')
history = pickle.load(open("history.p", "rb"))

# Load the unique_word_index mapping
with open('unique_word_index.pkl', 'rb') as f:
    unique_word_index = pickle.load(f)

# Reverse mapping from index to word
indices_char = dict((i, c) for c, i in unique_word_index.items())

# Prediction functions
def prepare_input(text):
    words = text.split()[-WORD_LENGTH:]
    x = np.zeros((1, WORD_LENGTH, len(unique_words)))
    for t, word in enumerate(words):
        if word in unique_word_index:
            x[0, t, unique_word_index[word]] = 1
    return x

def sample(preds, top_n=3):
    preds = np.log(np.asarray(preds).astype('float64'))
    exp_preds = np.exp(preds)
    preds = exp_preds / np.sum(exp_preds)
    return heapq.nlargest(top_n, range(len(preds)), preds.take)

# Modify the predict_completion function to limit recursion
def predict_completion(text, max_len=20):
    if len(text) >= max_len:
        return ''
    
    x = prepare_input(text)
    preds = model.predict(x, verbose=0)[0]
    next_index = sample(preds, 1)[0]
    next_char = indices_char[next_index]
    
    return next_char + predict_completion(text[1:] + next_char, max_len)



def predict_completions(text, n=3):
    x = prepare_input(text)
    preds = model.predict(x, verbose=0)[0]
    next_indices = sample(preds, n)
    return [indices_char[idx] + predict_completion(text[1:] + indices_char[idx]) for idx in next_indices]

# Sample quotes for prediction
quotes = [
    "It is not a lack of love, but a lack of friendship that makes unhappy marriages.",
    "That which does not kill us makes us stronger.",
    "I'm not upset that you lied to me, I'm upset that from now on I can't believe you.",
    "And those who were seen dancing were thought to be insane by those who could not hear the music.",
    "It is hard enough to remember my opinions, without also remembering my reasons for them!"
]

for q in quotes:
    seq = q[:40].lower()
    print(seq)
    print(predict_completions(seq, 5))
    print()

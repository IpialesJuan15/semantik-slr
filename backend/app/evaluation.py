from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import train_test_split

from .analysis import MODEL, semantic_model


def evaluate(articles, engine):
    labeled = [a for a in articles if a['decision'] in ('included','excluded')]
    labels = [int(a['decision']=='included') for a in labeled]
    counts = Counter(labels)
    if min(counts.get(0,0),counts.get(1,0)) < 5:
        raise ValueError('Para esta evaluación exploratoria necesitas al menos 5 incluidos y 5 excluidos etiquetados por una persona.')
    texts = [(a['title']+'\n'+a['abstract'])[:52000] for a in labeled]
    train, test = train_test_split(list(range(len(texts))), test_size=.4, stratify=labels, random_state=42)
    if engine == 'semantic':
        vectors = np.asarray(list(semantic_model().embed(texts,batch_size=8)))
        x_train, x_test = vectors[train], vectors[test]
        model_name = MODEL
    else:
        vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=12000, strip_accents='unicode')
        x_train = vectorizer.fit_transform([texts[i] for i in train])
        x_test = vectorizer.transform([texts[i] for i in test])
        model_name = 'TF-IDF ajustado solo en entrenamiento'
    classifier = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
    classifier.fit(x_train,[labels[i] for i in train])
    predicted = classifier.predict(x_test)
    expected = [labels[i] for i in test]
    precision, recall, f1, _ = precision_recall_fscore_support(expected,predicted,average='binary',zero_division=0)
    return {'engine':engine,'model':model_name,'classifier':'LogisticRegression','precision':float(precision),'recall':float(recall),'f1':float(f1),'confusion_matrix':confusion_matrix(expected,predicted,labels=[0,1]).tolist(),'matrix_labels':['excluded','included'],'training_count':len(train),'test_count':len(test),'train_ids':[labeled[i]['id'] for i in train],'test_ids':[labeled[i]['id'] for i in test],'seed':42,'scope':'exploratory_holdout','limitation':'Evaluación exploratoria de clasificación con etiquetas locales. No mide cobertura de búsqueda ni constituye una validación independiente de la tesis. Reutilizar este conjunto para ajustar el modelo invalida su independencia.'}

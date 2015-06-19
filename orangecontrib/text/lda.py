import numpy as np
from gensim import corpora, models, matutils

from Orange.data.table import Table
from Orange.data.domain import Domain, ContinuousVariable, StringVariable

def chunk_list(l, num):
    num = min(len(l), num)
    avg = len(l) / float(num)
    out = []
    last = 0.0
    while last < len(l):
        out.append(l[int(last):int(last + avg)])
        last += avg
    return out


class LDA:
    def __init__(self, text, num_topics=5, callback=None):
        """
        Wraper for Gensim LDA model.

        :param text: Preprocessed text.
        :param num_topics: Number of topics to infer.
        :return: None
        """
        self.text = text
        self.num_topics = num_topics

        # generate dict and corpus
        dictionary = corpora.Dictionary(self.text)
        corpus = [dictionary.doc2bow(t) for t in self.text]

        lda = models.LdaModel(id2word=dictionary, num_topics=self.num_topics)
        done = 0
        for i, part in enumerate(chunk_list(corpus, 95)):
            lda.update(part)
            done += len(part)
            callback(95.0*done/len(corpus))

        corpus = lda[corpus]
        topics = lda.show_topics(num_topics=-1, num_words=3, formatted=False)
        names = [', '.join([i[1] for i in t]) for t in topics]
        names = ['Topic{} ({})'.format(i, n) for i, n in enumerate(names, 1)]

        self.topic_names = names
        self.corpus = corpus
        self.lda = lda

    def insert_topics_into_corpus(self, corp_in):
        """
        Insert topical representation into corpus.

        :param corp_in: Corpus into whic we want to insert topical representations
        :return: `Orange.data.table.Table`
        """
        matrix = matutils.corpus2dense(self.corpus,
                                       num_terms=self.num_topics).T

        # Generate the new table.
        attr = [ContinuousVariable(n) for n in self.topic_names]
        domain = Domain(attr,
                        corp_in.domain.class_vars,
                        metas=corp_in.domain.metas)

        return Table.from_numpy(domain,
                                matrix,
                                Y=corp_in._Y,
                                metas=corp_in.metas)

    def get_topics_table(self):
        """
        Transform topics from gensim LDA model to table.

        :param lda: gensim LDA model.
        :return: `Orange.data.table.Table`.
        """
        topics = self.lda.show_topics(num_topics=-1, num_words=-1, formatted=False)
        num_topics = len(topics)
        num_words = max([len(it) for it in topics])

        data = np.zeros((num_words, 2*num_topics), dtype=object)

        for i, topic in enumerate(topics):
            data[:, 2*i] = [item[1] for item in topic]
            data[:, 2*i+1] = [item[0] for item in topic]

        metas = []
        for i in range(num_topics):
            metas.append(StringVariable(self.topic_names[i]))
            metas.append(ContinuousVariable("Topic{}_weights".format(i+1)))
            metas[-1]._out_format = '%.2e'

        domain = Domain([], metas=metas)
        return Table.from_numpy(domain,
                                X=np.zeros((num_words, 0)),
                                metas=data)
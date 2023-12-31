# -*- coding: utf-8 -*-
"""The Notebook.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1c3lkJUkN1-1lEvLP1_HZMXkpNDq8CmoZ

# **Welcome To the Notebook**

### **Task 1 - Loading our data**

Installing the pyspark using pip
"""

!pip install pyspark

"""Importing Modules"""

# importing spark session
from pyspark.sql import SparkSession

# data visualization modules
import matplotlib.pyplot as plt
import plotly.express as px

# pandas module
import pandas as pd

# pyspark SQL functions
from pyspark.sql.functions import col, when, count, udf

# pyspark data preprocessing modules
from pyspark.ml.feature import Imputer, StringIndexer, VectorAssembler, StandardScaler

# pyspark data modeling and model evaluation modules
from pyspark.ml.classification import DecisionTreeClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator

"""Building our Spark Session"""

spark = SparkSession.builder.appName("Customer_Churn_Prediction").getOrCreate()
spark

"""Loading our data"""

data = spark.read.format('csv').option("inferSchema", True).option('header', True).load("dataset.csv")
data.show(5)

"""Print the data schema to check out the data types"""

data.printSchema()

"""Get the data dimension"""

data.count()
data.columns

"""### **Task 2 - Exploratory Data Analysis**
- Distribution Analysis
- Correlation Analysis
- Univariate Analysis
- Finding Missing values

Let's define some lists to store different column names with different data types.
"""

numerical_columns = [name for name, typ in data.dtypes if typ == 'double' or typ == 'int']
categorical_columns = [name for name, typ in data.dtypes if typ == 'string']
data.select(numerical_columns).show()

"""Let's get all the numerical features and store them into a pandas dataframe."""

df = data.select(numerical_columns).toPandas()
df.head()

"""Let's create histograms to analyse the distribution of our numerical columns."""

fig = plt.figure()
ax = fig.gca()
df.hist(ax=ax, bins=20)
df.tenure.describe()



"""Let's generate the correlation matrix"""

df.corr()

"""Let's check the unique value count per each categorical variables"""

for column in categorical_columns:
  data.groupby(column).count()

"""
Let's find number of null values in all of our dataframe columns"""

for column in data.columns:
  data.select(count(when(col(column).isNull(), column)).alias(column)).show()

"""### **Task 3 - Data Preprocessing**
- Handling the missing values
- Removing the outliers

**Handling the missing values** <br>
Let's create a list of column names with missing values
"""

columns_with_missing_values = ["TotalCharges"]

"""Creating our Imputer"""

imputer = Imputer(inputCols=columns_with_missing_values, outputCols=columns_with_missing_values).setStrategy("mean")

"""Use Imputer to fill the missing values"""

imputer = imputer.fit(data)
data = imputer.transform(data)

"""Let's check the missing value counts again"""

data.select(count(when(col('TotalCharges').isNull(), "TotalCharges")).alias("TotalCharges")).show()

"""**Removing the outliers** <br>
Let's find the customer with the tenure higher than 100
"""

data.select('*').where(data.tenure > 100).show()

"""Let's drop the outlier row"""

data = data.filter(data.tenure < 100)
print(data.count())

"""### **Task 4 - Feature Preparation**
- Numerical Features
    - Vector Assembling
    - Numerical Scaling
- Categorical Features
    - String Indexing
    - Vector Assembling

- Combining the numerical and categorical feature vectors




**Feature Preparation - Numerical Features** <br>

`Vector Assembling --> Standard Scaling` <br>

**Vector Assembling** <br>
To apply our machine learning model we need to combine all of our numerical and categorical features into vectors. For now let's create a feature vector for our numerical columns.

"""

numerical_vector_assembler = VectorAssembler(inputCols=numerical_columns, outputCol='numerical_features_vector')
data = numerical_vector_assembler.transform(data)

"""**Numerical Scaling** <br>
Let's standardize all of our numerical features.
"""

scaler = StandardScaler(inputCol="numerical_features_vector", outputCol='numerical_features_scaled', withStd=True, withMean=True)
data = scaler.fit(data).transform(data)
data.show()

"""**Feature Preperation - Categorical Features** <br>

`String Indexing --> Vector Assembling` <br>

**String Indexing** <br>
We need to convert all the string columns to numeric columns.
"""

categorical_columns_indexed = [name + "_Indexed" for name in categorical_columns]

indexer = StringIndexer(inputCols = categorical_columns, outputCols=categorical_columns_indexed)
data = indexer.fit(data).transform(data)
data.show()

"""Let's combine all of our categorifal features in to one feature vector."""

# print(categorical_columns_indexed)

categorical_columns_indexed.remove("customerID_Indexed")
categorical_columns_indexed.remove("Churn_Indexed")

categorical_vector_assembler = VectorAssembler(inputCols=categorical_columns_indexed, outputCol="categorical_features_vector")
data = categorical_vector_assembler.transform(data)

data.show()

"""Now let's combine categorical and numerical feature vectors."""

final_vector_assembler = VectorAssembler(inputCols=['categorical_features_vector', "numerical_features_scaled"], outputCol='final_feature_vector')
data = final_vector_assembler.transform(data)

data.select(['final_feature_vector', 'Churn_Indexed']).show()

"""### **Task 5 - Model Training**
- Train and Test data splitting
- Creating our model
- Training our model
- Make initial predictions using our model

In this task, we are going to start training our model
"""

train, test = data.randomSplit([.7,.3], seed =100)

train.count()

"""Now let's create and train our desicion tree"""

dt = DecisionTreeClassifier(featuresCol='final_feature_vector', labelCol='Churn_Indexed', maxDepth=3)
model = dt.fit(train)

"""Let's make predictions on our test data"""

predictions_test = model.transform(test)
predictions_test.select(['Churn', 'prediction']).show()

"""### **Task 6 - Model Evaluation**
- Calculating area under the ROC curve for the `test` set
- Calculating area under the ROC curve for the `training` set
- Hyper parameter tuning
"""

evaluator = BinaryClassificationEvaluator(labelCol="Churn_Indexed")
auc_test = evaluator.evaluate(predictions_test, {evaluator.metricName : "areaUnderROC"})
auc_test

"""Let's get the AUC for our `training` set"""

predictions_train = model.transform(train)
auc_train = evaluator.evaluate(predictions_train, {evaluator.metricName : "areaUnderROC"})
auc_train

"""**Hyper parameter tuning**

Let's find the best `maxDepth` parameter for our DT model.
"""

def evaluate_dt(mode_params):
      test_accuracies = []
      train_accuracies = []

      for maxD in mode_params:
        # train the model based on the maxD
        decision_tree = DecisionTreeClassifier(featuresCol = 'final_feature_vector', labelCol = 'Churn_Indexed', maxDepth = maxD)
        dtModel = decision_tree.fit(train)

        # calculating test error
        predictions_test = dtModel.transform(test)
        evaluator = BinaryClassificationEvaluator(labelCol="Churn_Indexed")
        auc_test = evaluator.evaluate(predictions_test, {evaluator.metricName: "areaUnderROC"})
        # recording the accuracy
        test_accuracies.append(auc_test)

        # calculating training error
        predictions_training = dtModel.transform(train)
        evaluator = BinaryClassificationEvaluator(labelCol="Churn_Indexed")
        auc_training = evaluator.evaluate(predictions_training, {evaluator.metricName: "areaUnderROC"})
        train_accuracies.append(auc_training)

      return(test_accuracies, train_accuracies)

"""Let's define `params` list to evaluate our model iteratively with differe maxDepth parameter.  """

maxDepths = [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
test_accs, train_accs = evaluate_dt(maxDepths)

print(train_accs)
print(test_accs)

"""Let's visualize our results"""

df = pd.DataFrame()
df['maxDepth'] = maxDepths
df['trainAcc'] = train_accs
df['testAcc'] = test_accs

px.line(df, x='maxDepth', y=['trainAcc', 'testAcc'])

"""### **7 - Model Deployment**
- Giving Recommendations using our model

We were asked to recommend a solution to reduce the customer churn.
"""

feature_importance = model.featureImportances
scores = [score for i, score in enumerate(feature_importance)]
df = pd.DataFrame(scores, columns=['score'], index=categorical_columns_indexed+numerical_columns)
px.bar(df, y='score')

"""Let's create a bar chart to visualize the customer churn per contract type"""

df = data.groupby(['Contract', 'Churn']).count().toPandas()
px.bar(df, x='Contract', y='count', color='Churn')

"""The bar chart displays the number of churned customers based on their contract type. It is evident that customers with a "Month-to-month" contract have a higher churn rate compared to those with "One year" or "Two year" contracts. As a recommendation, the telecommunication company could consider offering incentives or discounts to encourage customers with month-to-month contracts to switch to longer-term contracts."""
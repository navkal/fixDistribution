import csv
import pandas as pd
import natsort

# Read the old distribution file and drop blank lines
df = pd.read_csv( 'old_distribution.csv', index_col=['path'] )
df = df.dropna( how='all' )
df = df.fillna('')

# Create dictionary of sorted paths
aSortedPaths = natsort.natsorted( df.index.values.tolist() )
dcSortedPaths = {}
i = 0
for sPath in aSortedPaths:
    dcSortedPaths[sPath] = i
    i += 1

# Sort dataframe on path
df = df.reset_index()
df['sort'] = df['path'].map( dcSortedPaths )
df = df.sort_values( by=['sort'] )
df = df.drop( ['sort'], axis=1 )
df = df.reset_index( drop=True )

dfPanels = pd.DataFrame( df.loc[df['type'] == 'Panel']['path'] )
dfPanels.to_csv( 'groupByBase.csv', index=None )

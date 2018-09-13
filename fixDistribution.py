import csv
import pandas as pd
import natsort
import shutil

# Replace circuit representing phase B or phase C connection
def replacePhaseCircuit( df, sParentPath, sPath, sPhaseNum ):

    sPhasePath = sParentPath + '.' + sPhaseNum
    sDropPath = ''
    print( '---' )
    print( 'FOR', sPath )

    if sPhasePath in df.index.values:
        # Found exact match
        sDropPath = sPhasePath
    else:
        # Look for approximate match
        sHyphenPath = sPhasePath + '-'
        dfMatch = df.loc[df.index.str.startswith( sHyphenPath )]

        if len( dfMatch ) > 0:
            dfMatch = dfMatch.loc[~dfMatch.index.str.slice( len( sHyphenPath ) ).str.contains( '\.' )]
            if len( dfMatch ) == 1:
                sDropPath = dfMatch.index.values[0]

    if sDropPath:
        print( 'REPLACING\n', sDropPath, df.loc[sDropPath].values, '\nWITH\n', sPhasePath, df.loc[sPath].values )
        df = df.drop( sDropPath )
    else:
        print( 'ADDING\n', df.loc[sPath].values )


    print( '---' )
    srPhase = df.loc[sPath].copy()
    srPhase = srPhase.rename( sPhasePath )
    df = df.append( srPhase )
    return df


# Read file mapping panels to information on how to group circuits for multi-phase connections
dfGroupBy = pd.read_csv( 'groupBy.csv', index_col=['path'] )

# Read the old distribution file and drop blank lines
df = pd.read_csv( 'old_distribution.csv', index_col=['path'] )
df = df.dropna( how='all' )
df = df.fillna('')
iOldLines = len( df )

# Add phase-related columns to dataframe
df.insert( loc=1, column='phase_c', value='' )
df.insert( loc=1, column='phase_b', value='' )
df.insert( loc=1, column='three_phase', value='' )


# Loop until all cases of deficient parentage have been corrected

iFixed = 0

bContinue = True

while( bContinue ):

    bContinue = False

    # Extract all panels and transformers into a subset dataframe
    dfPanTran = df.loc[ df['type'].isin( ['Panel','Transformer'] ) ]

    # Traverse dataframe of panels and transformers until we encounter an element with deficient parentage
    for sPath in dfPanTran.index.values:

        # Get path of parent
        aPath = sPath.split( '.' )
        sParentPath = '.'.join( aPath[:-1] )

        # If parent is a panel...
        if sParentPath and ( df.loc[sParentPath]['type'] == 'Panel' ):

            # Current element is a Panel or Transformer directly descended from a Panel.
            # Insert circuit into the hierarchy above the element.

            # Generate new path that includes Circuit as parent
            sTail = aPath[-1]
            aTail = sTail.split( '-', maxsplit=1 )
            sName = aTail[1]
            sNewPath = sPath + '.' + sName

            # Create copy of current element with updated path
            srNewPath = df.loc[sPath].copy()
            srNewPath = srNewPath.rename( sNewPath )

            # Update paths of all descendants of current element, to include inserted Circuit
            sPattern = '^' + ( sPath + '.' ).replace( '.', '\.' )
            sReplace = sNewPath + '.'
            df = df.reset_index()
            df['path'] = df['path'].str.replace( pat=sPattern, repl=sReplace, n=1 )
            df = df.set_index( ['path'] )

            # Change original row to Circuit
            sConnectedTo = 'Connected to ' + df.at[sPath, 'type'] + ' ' + sName
            df.at[sPath, 'type'] = 'Circuit'
            df.at[sPath, 'room'] = ''
            df.at[sPath, 'description'] = sConnectedTo
            df.at[sPath, 'devices'] = ''

            # Append element with new path to dataframe
            df = df.append( srNewPath )

            # Update the groupBy dataframe
            dfGroupBy = dfGroupBy.reset_index()
            dfGroupBy['path'] = dfGroupBy['path'].str.replace( pat=sPattern, repl=sReplace, n=1 )
            dfGroupBy['path'] = dfGroupBy['path'].str.replace( pat='^' + ( sPath ).replace( '.', '\.' ) + '$', repl=sNewPath )
            dfGroupBy = dfGroupBy.set_index( ['path'] )

            # Insert index values for phases B and C
            nPhaseIncrement = dfGroupBy.loc[sParentPath]['groupBy']

            sPhases = ''
            if nPhaseIncrement:
                iCircuit = aTail[0]
                if iCircuit.isdigit():
                    # Set circuit indices for each phase
                    nA = int( aTail[0] )
                    nB = nA + nPhaseIncrement
                    nC = nB + nPhaseIncrement
                    sB = str( nB )
                    sC = str( nC )
                    sPhases = ' (B:' + sB + ',C:' + sC + ')'

                    # Save indices in Panel/Transformer element
                    df.at[sNewPath, 'phase_b'] = sB
                    df.at[sNewPath, 'phase_c'] = sC

                    # Replace phase B and C circuits
                    df = replacePhaseCircuit( df, sParentPath, sPath, sB )
                    df = replacePhaseCircuit( df, sParentPath, sPath, sC )
            elif sName == 'TLGD':
                print( '!!! SPECIAL CASE !!!' )
                df = replacePhaseCircuit( df, sParentPath, sPath, '7' )
                df = replacePhaseCircuit( df, sParentPath, sPath, '8' )

            # Report
            iFixed += 1
            print( str( iFixed ) + ': ' + str( df.loc[sNewPath]['type'] ) + ' - ' + sPath + ' --> ' + sNewPath + sPhases   );

            # Loop control:

            # Set flag to continue outer loop, to refresh the list of Panels and Transformers
            bContinue = True

            # Exit inner loop
            break

# Set three_phase flags for all panels
dfPan = df.loc[ df['type'] == 'Panel' ]
for sPath in dfPan.index.values:
    df.at[sPath, 'three_phase'] = int( dfGroupBy.loc[sPath]['groupBy'] == 0 )

# Eliminate superfluous voltage settings
# Panels - high voltage at root; otherwise empty
dfPan = df.loc[ df['type'] == 'Panel' ]
for sPath in dfPan.index.values:
    df.at[sPath, 'voltage'] = ''
df.at['MSWB', 'voltage'] = '277/480'
# Transformers - low voltage
dfTran = df.loc[ df['type'] == 'Transformer' ]
for sPath in dfTran.index.values:
    df.at[sPath, 'voltage'] = '120/208'
# Circuits - empty
dfCir = df.loc[ df['type'] == 'Circuit' ]
for sPath in dfCir.index.values:
    df.at[sPath, 'voltage'] = ''


print( '' )
print( '' )
print( '===> Original line count:', iOldLines )
print( '===> New line count:', len( df ) )
print( '' )
print( '' )

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

# Generate CSV
aBlank = [''] * len( df.columns.values )
sPath = ''
sPrevPath = ''

with open( 'distribution.csv', 'w' ) as csvfile:
    writer = csv.writer( csvfile, lineterminator='\n' )
    writer.writerow( df.columns.values )

    for i in df.index.values:
        # Get next line
        srLine = df.iloc[i]

        # Track path and type
        sPrevPath = sPath
        sPath = srLine.loc['path']
        sType = srLine.loc['type']

        # Optionally write blank line to CSV
        if sType in ('Panel', 'Transformer') or ( len( sPath.split( '.' ) ) < len( sPrevPath.split( '.' ) ) ):
            writer.writerow( aBlank )

        # Write line to CSV
        aLine = srLine.tolist()
        writer.writerow( aLine )

shutil.copy2( 'distribution.csv', '../makeDb/demo_distribution.csv' )
shutil.copy2( 'distribution.csv', '../makeDb/ahs_distribution.csv' )
shutil.copy2( 'distribution.csv', '../makeDb/bancroft_distribution.csv' )


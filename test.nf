process foo {
  output:
  path '*.txt'

  script:
  '''
  echo Hello there! > file1.txt
  echo What a beautiful day > file2.txt
  echo I hope you are having fun! > file3.txt 
  ''' 
}

process bar {
  debug true
  input: 
  path x

  script:
  """
  cat $x
  """
}

workflow {
  foo | flatten | bar
}
grammar ExcelFormula;

// Parser rules
formula: '=' expression EOF;

expression
    : logicalExpr
    ;

logicalExpr
    : logicalExpr ('&&' | '||') compareExpr
    | compareExpr
    ;

compareExpr
    : compareExpr ('=' | '<>' | '<' | '>' | '<=' | '>=') addExpr
    | addExpr
    ;

addExpr
    : addExpr ('+' | '-') multExpr
    | multExpr
    ;

multExpr
    : multExpr ('*' | '/' | '^') unaryExpr
    | unaryExpr
    ;

unaryExpr
    : '-' atom
    | atom
    ;

atom
    : functionCall
    | columnRef
    | literal
    | '(' expression ')'
    ;

functionCall: IDENTIFIER '(' (expression (',' expression)*)? ')';

columnRef: IDENTIFIER;

literal
    : NUMBER
    | STRING
    | BOOLEAN
    | DATE
    ;

// Lexer rules
NUMBER: ('-'? [0-9]+ ('.' [0-9]*)? | '-'? '.' [0-9]+) ([eE] [+-]? [0-9]+)?;
STRING: '"' (~["\\] | '\\' .)* '"';
BOOLEAN: 'TRUE' | 'FALSE';
DATE: [0-9]{4} '-' [0-9]{2} '-' [0-9]{2};
IDENTIFIER: [a-zA-Z][a-zA-Z0-9_]*;
WHITESPACE: [ \t\r\n]+ -> skip;
OPERATOR: '+' | '-' | '*' | '/' | '^' | '=' | '<>' | '<' | '>' | '<=' | '>=' | '&&' | '||';
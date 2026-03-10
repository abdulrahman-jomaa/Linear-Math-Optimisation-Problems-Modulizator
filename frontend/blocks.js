// ==========================================
// 1. DEFINITIONS (Sets, Parameters, Variables)
// ==========================================

Blockly.Blocks['set_def'] = {
    init: function(){
        this.appendDummyInput()
            .appendField("Define Set")
            .appendField(new Blockly.FieldTextInput("items"), "NAME")
            .appendField("=")
            .appendField(new Blockly.FieldTextInput("0,1,2,3"), "VALUES");
        this.setPreviousStatement(true);
        this.setNextStatement(true);
        this.setColour(330);
    }
};

Blockly.Blocks['param_def'] = {
    init: function(){
        this.appendDummyInput()
            .appendField("Define Parameter")
            .appendField(new Blockly.FieldTextInput("size"), "NAME")
            .appendField("=")
            .appendField(new Blockly.FieldTextInput("4,5,6,3"), "VALUES");
        this.setPreviousStatement(true);
        this.setNextStatement(true);
        this.setColour(330);
    }
};

Blockly.Blocks['var_def'] = {
    init: function(){
        this.appendDummyInput()
            .appendField("Define")
            .appendField(new Blockly.FieldDropdown([
                ["binary","binary"],
                ["integer","integer"],["continuous","continuous"]
            ]), "TYPE")
            .appendField("Variable")
            .appendField(new Blockly.FieldTextInput("x"), "NAME")
            .appendField("over sets")
            .appendField(new Blockly.FieldTextInput("items, bins"), "SETS");
        this.setPreviousStatement(true);
        this.setNextStatement(true);
        this.setColour(200);
    }
};


// ==========================================
// 2. OBJECTIVES (Minimize / Maximize)
// ==========================================

Blockly.Blocks['minimize'] = {
    init: function(){
        this.appendDummyInput()
            .appendField("Minimize");
        this.appendValueInput("EXPR");
        this.setColour(20);
    }
};

Blockly.Blocks['maximize'] = {
    init: function(){
        this.appendDummyInput()
            .appendField("Maximize");
        this.appendValueInput("EXPR");
        this.setColour(20);
    }
};


// ==========================================
// 3. MATH (Sum, Multiply)
// ==========================================

Blockly.Blocks['sum'] = {
    init: function(){
        this.appendDummyInput()
            .appendField("sum")
            .appendField(new Blockly.FieldTextInput("j"), "INDEX")
            .appendField("in")
            .appendField(new Blockly.FieldTextInput("bins"), "SET");
        this.appendValueInput("EXPR");
        this.setOutput(true);
        this.setColour(120);
    }
};

Blockly.Blocks['multiply'] = {
    init: function(){
        this.appendValueInput("A");
        this.appendDummyInput()
            .appendField("*");
        this.appendValueInput("B");
        this.setOutput(true);
        this.setColour(160);
    }
};


// ==========================================
// 4. USAGE (Variables, Parameters inside math)
// ==========================================

Blockly.Blocks['variable'] = {
    init: function(){
        this.appendDummyInput()
            .appendField("var")
            .appendField(new Blockly.FieldTextInput("x"), "NAME")
            .appendField("[")
            .appendField(new Blockly.FieldTextInput("i, j"), "INDEX")
            .appendField("]");
        this.setOutput(true);
        this.setColour(200);
    }
};

Blockly.Blocks['parameter'] = {
    init: function(){
        this.appendDummyInput()
            .appendField("param")
            .appendField(new Blockly.FieldTextInput("size"), "NAME")
            .appendField("[")
            .appendField(new Blockly.FieldTextInput("i"), "INDEX")
            .appendField("]");
        this.setOutput(true);
        this.setColour(260);
    }
};


// ==========================================
// 5. CONSTRAINTS (For All, Equals/Inequals)
// ==========================================

Blockly.Blocks['forall'] = {
    init: function(){
        this.appendDummyInput()
            .appendField("For all")
            .appendField(new Blockly.FieldTextInput("i"), "INDEX")
            .appendField("in set")
            .appendField(new Blockly.FieldTextInput("items"), "SET");
        this.appendStatementInput("CONSTRAINTS")
            .setCheck(null);
        this.setPreviousStatement(true);
        this.setNextStatement(true);
        this.setColour(290);
    }
};

Blockly.Blocks['constraint'] = {
    init: function(){
        this.appendValueInput("LEFT");
        this.appendDummyInput()
            .appendField(new Blockly.FieldDropdown([["=","=="],
                ["≤","<="],
                ["≥",">="]
            ]), "OP");
        this.appendValueInput("RIGHT");
        this.setPreviousStatement(true);
        this.setNextStatement(true);
        this.setColour(0);
    }
};

Blockly.Blocks['math_number'] = {
  init: function() {
    this.appendDummyInput()
        .appendField(new Blockly.FieldNumber(0), "NUM");
    this.setOutput(true, 'Number');
    this.setColour(120);
    this.setTooltip("A literal number.");
  }
};
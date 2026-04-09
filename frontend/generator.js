// ==========================================
// GENERATE FUNCTION (Block -> JSON Object)
// ==========================================
function generate(block) {
    if (!block) return null;

    switch (block.type) {
        // --- THIS FIXES THE 'right' ERROR ---
        case "math_number":
            return parseFloat(block.getFieldValue('NUM'));

        // DEFINITIONS
        case "set_def":
            return {
                type: "set_def",
                name: block.getFieldValue("NAME"),
                values: block.getFieldValue("VALUES").split(",").map(x => isNaN(x) ? x.trim() : Number(x))
            };
        case "param_def":
            return {
                type: "param_def",
                name: block.getFieldValue("NAME"),
                values: block.getFieldValue("VALUES").split(",").map(Number)
            };
        case "var_def":
            let rawSets = block.getFieldValue("SETS");
            let setsArray = rawSets ? rawSets.split(",").map(s => s.trim()).filter(s => s !== "") : [];
            return {
                type: "var_def",
                var_def: { name: block.getFieldValue("NAME"), type: block.getFieldValue("TYPE"), sets: setsArray }
            };

        // OBJECTIVES
        case "minimize":
            return { objective: { sense: "minimize", expr: generate(block.getInputTargetBlock("EXPR")) } };
        case "maximize":
            return { objective: { sense: "maximize", expr: generate(block.getInputTargetBlock("EXPR")) } };

        // MATH & USAGE
        case "variable":
            let vIndex = block.getFieldValue("INDEX").split(",").map(s => s.trim()).filter(s => s !== "");
            return { var: block.getFieldValue("NAME"), index: vIndex.length > 0 ? vIndex : undefined };
        case "parameter":
            let pIndex = block.getFieldValue("INDEX").split(",").map(s => s.trim()).filter(s => s !== "");
            return { param: block.getFieldValue("NAME"), index: pIndex.length > 0 ? pIndex : undefined };
        case "sum":
            return { sum: { index: block.getFieldValue("INDEX"), set: block.getFieldValue("SET"), expr: generate(block.getInputTargetBlock("EXPR")) } };
        case "multiply":
            return { mul: [generate(block.getInputTargetBlock("A")), generate(block.getInputTargetBlock("B"))] };

        // CONSTRAINTS
        case "constraint":
            return { op: block.getFieldValue("OP"), left: generate(block.getInputTargetBlock("LEFT")), right: generate(block.getInputTargetBlock("RIGHT")) };
        case "forall":
            let forall_constraints = [];
            let currentBlock = block.getInputTargetBlock("CONSTRAINTS");
            while (currentBlock) {
                let inner_c = generate(currentBlock);
                if (inner_c) {
                    forall_constraints.push({ forall: { index: block.getFieldValue("INDEX"), set: block.getFieldValue("SET") }, expr: inner_c });
                }
                currentBlock = currentBlock.getNextBlock();
            }
            return { type: "forall_wrapper", list: forall_constraints };
        case "forall_where":
            let fw_constraints = [];
            let fw_currentBlock = block.getInputTargetBlock("CONSTRAINTS");
            const opMap = { "EQ":"==", "LE":"<=", "GE":">=", "LT":"<", "GT":">", "NEQ":"!=" };
            let rawOp = block.getFieldValue("OP");
            let realOp = opMap[rawOp] || rawOp;

            while (fw_currentBlock) {
                let inner_c = generate(fw_currentBlock);
                if (inner_c) {
                    fw_constraints.push({
                        forall: {
                            index: block.getFieldValue("INDEX"),
                            set: block.getFieldValue("SET"),
                            condition: {
                                left: block.getFieldValue("LEFT"),
                                op: realOp,
                                right: block.getFieldValue("RIGHT")
                            }
                        },
                        expr: inner_c
                    });
                }
                fw_currentBlock = fw_currentBlock.getNextBlock();
            }
            return { type: "forall_wrapper", list: fw_constraints };
    }
}


// ==========================================
// EXPORT FUNCTION (Called by the 'Preview' button)
// ==========================================
function exportJSON() {
    const model = buildModelFromWorkspace();
    document.getElementById("output").textContent = JSON.stringify(model, null, 2);
}


// ==========================================
// SOLVE FUNCTION (Connects to Python Backend)
// ==========================================
async function solveModel() {
    document.getElementById("output").textContent = "Building model and solving with SCIP... Please wait ⚙️";
    const model = buildModelFromWorkspace();

    try {
        const response = await fetch('/solve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_json: model })
        });

        const result = await response.json();
        document.getElementById("output").textContent = JSON.stringify(result, null, 2);

        // Call the visualization function after a successful solve
        renderVisualization(result, model);

    } catch (error) {
        document.getElementById("output").textContent = "Connection Error: Is the Python server running?";
        document.getElementById("visualizationDiv").innerHTML = ""; // Clear viz on error
    }
}


// ==========================================
// HELPER FUNCTION (Reads all blocks from workspace)
// ==========================================
function buildModelFromWorkspace() {
    const topBlocks = workspace.getTopBlocks(true);
    let model = {
        name: "visual_model",
        sets: {},
        parameters: {},
        variables:[],
        objective: null,
        constraints:[]
    };
    for (let topBlock of topBlocks) {
        let currentBlock = topBlock;
        while (currentBlock) {
            let j = generate(currentBlock);
            if (j) {
                if (j.objective) model.objective = j.objective;
                else if (j.type === "set_def") model.sets[j.name] = j.values;
                else if (j.type === "param_def") model.parameters[j.name] = j.values;
                else if (j.type === "var_def") model.variables.push(j.var_def);
                else if (j.type === "forall_wrapper") model.constraints.push(...j.list);
                else if (j.op) model.constraints.push({ expr: j });
            }
            currentBlock = currentBlock.getNextBlock();
        }
    }
    return model;
}


// ==========================================
// VISUALIZATION FUNCTION (Draws the result)
// ==========================================
function renderVisualization(result, model) {
    const visDiv = document.getElementById("visualizationDiv");
    visDiv.innerHTML = ""; // Clear any previous visualization

    if (result.status !== "optimal" || !result.solution) return;

    const binsContent = {};
    for (const variableName in result.solution) {
        if (variableName.startsWith("x(")) {
            // This regex handles both "x(0,1)" and "x(0, 1)"
            const match = variableName.match(/\((\d+),\s*(\d+)\)/);
            if (match) {
                const itemIndex = parseInt(match[1]);
                const binIndex = parseInt(match[2]);
                if (!binsContent[binIndex]) binsContent[binIndex] = [];
                binsContent[binIndex].push(itemIndex);
            }
        }
    }

    // Don't draw anything if no items were packed
    if (Object.keys(binsContent).length === 0) return;

    for (const binIndex in binsContent) {
        const binDiv = document.createElement("div");
        binDiv.className = "bin";
        binDiv.innerHTML = `<h3>Bin ${binIndex}</h3>`;

        let totalSize = 0;
        const itemsInBin = binsContent[binIndex];
        itemsInBin.forEach(itemIndex => {
            const itemDiv = document.createElement("div");
            itemDiv.className = "item";
            const itemSize = model.parameters.size[itemIndex];
            itemDiv.textContent = `Item ${itemIndex} (Size: ${itemSize})`;
            binDiv.appendChild(itemDiv);
            totalSize += itemSize;
        });

        const footer = document.createElement("p");
        footer.style.marginTop = "10px";
        footer.style.fontSize = "12px";
        footer.innerHTML = `<b>Total Size: ${totalSize} / ${model.parameters.capacity[binIndex]}</b>`;
        binDiv.appendChild(footer);

        visDiv.appendChild(binDiv);
    }
}
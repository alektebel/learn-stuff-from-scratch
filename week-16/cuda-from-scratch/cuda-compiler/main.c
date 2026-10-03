/*
 * Tiny CUDA Compiler - Entry Point
 *
 * Compiles a CUDA kernel source file to PTX (Parallel Thread eXecution)
 * assembly that can be loaded and run on any NVIDIA GPU.
 *
 * Pipeline:
 *   source (.cu)  →  Lexer  →  tokens
 *                 →  Parser →  AST
 *                 →  Codegen→  PTX (.ptx)
 *
 * Usage:
 *   cuda_compiler <input.cu> [-o output.ptx] [-arch sm_XX] [-tokens] [-ast]
 *
 * Options:
 *   -o FILE      Write PTX to FILE instead of stdout
 *   -arch ARCH   Target compute capability (default: sm_60)
 *   -tokens      Dump the token stream and exit (debug)
 *
 * Example:
 *   ./cuda_compiler tests/vector_add.cu -o vector_add.ptx -arch sm_86
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lexer.h"
#include "ast.h"

/* ── Declared in parser.c ── */
ASTNode *parse(Lexer *lex);

/* ── Declared in codegen.c ── */
void codegen(ASTNode *program, FILE *out, const char *target_arch);

/* -----------------------------------------------------------------------
 * Read an entire file into a heap-allocated NUL-terminated string.
 * Returns NULL on error.
 * ----------------------------------------------------------------------- */
static char *read_file(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) {
        perror(path);
        return NULL;
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        perror("fseek");
        fclose(f);
        return NULL;
    }
    long size = ftell(f);
    if (size < 0) {
        perror("ftell");
        fclose(f);
        return NULL;
    }
    rewind(f);

    char *buf = (char *)malloc((size_t)size + 1);
    if (!buf) {
        fprintf(stderr, "Out of memory\n");
        fclose(f);
        return NULL;
    }
    size_t nread = fread(buf, 1, (size_t)size, f);
    buf[nread] = '\0';
    fclose(f);
    return buf;
}

static void print_usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s <input.cu> [-o output.ptx] [-arch sm_XX] [-tokens]\n"
            "\n"
            "Options:\n"
            "  -o FILE      Output PTX file (default: stdout)\n"
            "  -arch ARCH   Target GPU architecture (default: sm_60)\n"
            "  -tokens      Print token stream and exit (debug mode)\n"
            "\n"
            "Example:\n"
            "  %s tests/vector_add.cu -o vector_add.ptx -arch sm_86\n",
            prog, prog);
}

/* -----------------------------------------------------------------------
 * main
 * ----------------------------------------------------------------------- */
int main(int argc, char **argv)
{
    const char *input_file  = NULL;
    const char *output_file = NULL;
    const char *target_arch = "sm_60";
    int         print_tokens = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) {
            output_file = argv[++i];
        } else if (strcmp(argv[i], "-arch") == 0 && i + 1 < argc) {
            target_arch = argv[++i];
        } else if (strcmp(argv[i], "-tokens") == 0) {
            print_tokens = 1;
        } else if (argv[i][0] != '-') {
            input_file = argv[i];
        } else {
            fprintf(stderr, "Unknown option: %s\n\n", argv[i]);
            print_usage(argv[0]);
            return 1;
        }
    }

    if (!input_file) {
        print_usage(argv[0]);
        return 1;
    }

    /* ── Phase 0: read source ────────────────────────────────────────── */
    char *source = read_file(input_file);
    if (!source) return 1;

    fprintf(stderr, "Tiny CUDA Compiler\n");
    fprintf(stderr, "  Input  : %s\n", input_file);
    fprintf(stderr, "  Target : %s\n", target_arch);

    /* ── Phase 1: lexical analysis (optional dump) ───────────────────── */
    if (print_tokens) {
        fprintf(stderr, "\n=== Token Stream ===\n");
        Lexer dbg_lex;
        lexer_init(&dbg_lex, source);
        Token tok;
        while ((tok = lexer_next(&dbg_lex)).type != TOK_EOF) {
            fprintf(stderr, "[%3d:%2d]  %-20s  '%s'\n",
                    tok.line, tok.col, token_type_name(tok.type), tok.value);
        }
        fprintf(stderr, "=== End Tokens ===\n\n");
    }

    /* ── Phase 2: parse ──────────────────────────────────────────────── */
    fprintf(stderr, "  Phase 1 : Lexical analysis ...\n");
    fprintf(stderr, "  Phase 2 : Parsing ...\n");
    Lexer lex;
    lexer_init(&lex, source);
    ASTNode *program = parse(&lex);

    if (program->program.kernels.count == 0) {
        fprintf(stderr, "Warning: no __global__ kernels found in %s\n",
                input_file);
    } else {
        fprintf(stderr, "  Kernels : %d found\n",
                program->program.kernels.count);
        for (int i = 0; i < program->program.kernels.count; i++) {
            fprintf(stderr, "    [%d] %s\n", i + 1,
                    program->program.kernels.items[i]->kernel_func.name);
        }
    }

    /* ── Phase 3: code generation ────────────────────────────────────── */
    fprintf(stderr, "  Phase 3 : Generating PTX ...\n");

    FILE *out = stdout;
    if (output_file) {
        out = fopen(output_file, "w");
        if (!out) {
            perror(output_file);
            free(source);
            return 1;
        }
    }

    codegen(program, out, target_arch);

    if (output_file) {
        fclose(out);
        fprintf(stderr, "  Output  : %s\n", output_file);
    }

    fprintf(stderr, "  Done.\n");

    free(source);
    return 0;
}

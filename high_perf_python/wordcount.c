#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s filename\n", argv[0]);
        return 1;
    }

    FILE *file = fopen(argv[1], "r");
    if (!file) {
        perror("Error opening file");
        return 1;
    }

    int ch;
    int word_count = 0;
    int in_word = 0;

    while ((ch = fgetc(file)) != EOF) {
        if (isspace(ch)) {
            if (in_word) {
                in_word = 0;
                word_count++;
            }
        } else {
            in_word = 1;
        }
    }

    // If the last character was part of a word, we need to count that word.
    if (in_word) {
        word_count++;
    }

    fclose(file);
    printf("Number of words: %d\n", word_count);

    return 0;
}
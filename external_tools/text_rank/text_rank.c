/**
 * TextRank Algorithm for Text Compression
 * 
 * Implements a simplified TextRank algorithm to compress text while preserving
 * key information. This tool receives text via JSON on stdin and outputs
 * compressed text via JSON on stdout.
 */

#define _POSIX_C_SOURCE 200809L  /* For strdup */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#define MAX_SENTENCES 1000
#define MAX_WORDS 1000
#define MAX_WORD_LEN 100
#define MAX_TEXT_LEN 100000
#define MAX_SENTENCE_LEN 5000

typedef struct {
    char *text;
    double score;
    int index;
    int word_count;
    char **words;
} Sentence;

// Function prototypes
char *read_input();
char *parse_json_string(const char *json, const char *key);
double parse_json_double(const char *json, const char *key);
int parse_json_int(const char *json, const char *key);
void split_text_into_sentences(char *text, Sentence *sentences, int *sentence_count);
void extract_words(Sentence *sentence);
double calculate_similarity(Sentence *s1, Sentence *s2);
void text_rank(Sentence *sentences, int sentence_count, double damping, int iterations);
void select_top_sentences(Sentence *sentences, int sentence_count, Sentence *selected, 
                         int *selected_count, double compression_ratio);
void free_sentences(Sentence *sentences, int sentence_count);
void output_json(Sentence *selected, int selected_count);
char *trim(char *str);
int compare_sentences_by_index(const void *a, const void *b);
int is_separator(char c);

int main() {
    char *json_input = read_input();
    if (!json_input) {
        fprintf(stderr, "Error: Failed to read input\n");
        return 1;
    }

    // Parse required parameter: text
    char *text = parse_json_string(json_input, "text");
    if (!text) {
        fprintf(stderr, "{\"error\": \"Missing required parameter: text\"}\n");
        free(json_input);
        return 1;
    }

    // Parse optional parameters with defaults
    char *damping_str = parse_json_string(json_input, "damping_factor");
    double damping_factor = 0.85;  // default
    if (damping_str) {
        damping_factor = atof(damping_str);
        free(damping_str);
        if (damping_factor <= 0 || damping_factor > 1) damping_factor = 0.85;
    }
    
    char *iterations_str = parse_json_string(json_input, "iterations");
    int iterations = 50;  // default
    if (iterations_str) {
        iterations = atoi(iterations_str);
        free(iterations_str);
        if (iterations <= 0) iterations = 50;
    }
    
    char *compression_str = parse_json_string(json_input, "compression_ratio");
    double compression_ratio = 0.5;  // default
    if (compression_str) {
        compression_ratio = atof(compression_str);
        free(compression_str);
        if (compression_ratio <= 0 || compression_ratio > 1) compression_ratio = 0.5;
    }

    // Process the text
    Sentence sentences[MAX_SENTENCES] = {0};
    int sentence_count = 0;
    
    split_text_into_sentences(text, sentences, &sentence_count);
    
    // If we have too few sentences, just return the original text
    if (sentence_count <= 2) {
        printf("{\"compressed_text\": \"%s\", \"compression_ratio\": 1.0}\n", text);
        free(text);
        free(json_input);
        return 0;
    }

    // If text is too short (less than 10 words), just return it
    int word_count = 0;
    for (int i = 0; text[i]; i++) {
        if (text[i] == ' ') word_count++;
    }
    if (word_count < 10) {
        printf("{\"compressed_text\": \"%s\", \"compression_ratio\": 1.0}\n", text);
        free(text);
        free(json_input);
        return 0;
    }
    
    // Extract words for each sentence
    for (int i = 0; i < sentence_count; i++) {
        extract_words(&sentences[i]);
    }
    
    // Apply TextRank algorithm
    text_rank(sentences, sentence_count, damping_factor, iterations);
    
    // Select top sentences
    Sentence selected[MAX_SENTENCES] = {0};
    int selected_count = 0;
    select_top_sentences(sentences, sentence_count, selected, &selected_count, compression_ratio);
    
    // Output compressed text
    output_json(selected, selected_count);
    
    // Clean up
    free_sentences(sentences, sentence_count);
    free(text);
    free(json_input);
    
    return 0;
}

char *read_input() {
    char buffer[1024];
    char *input = malloc(1);
    if (!input) return NULL;
    
    input[0] = '\0';
    size_t input_len = 0;
    
    while (fgets(buffer, sizeof(buffer), stdin)) {
        size_t buffer_len = strlen(buffer);
        char *new_input = realloc(input, input_len + buffer_len + 1);
        
        if (!new_input) {
            free(input);
            return NULL;
        }
        
        input = new_input;
        strcpy(input + input_len, buffer);
        input_len += buffer_len;
    }
    
    return input;
}

char *parse_json_string(const char *json, const char *key) {
    char search_key[100];
    sprintf(search_key, "\"%s\"", key);
    
    char *key_pos = strstr(json, search_key);
    if (!key_pos) return NULL;
    
    key_pos = strchr(key_pos + strlen(search_key), ':');
    if (!key_pos) return NULL;
    
    key_pos = strchr(key_pos + 1, '"');
    if (!key_pos) return NULL;
    
    char *end_pos = strchr(key_pos + 1, '"');
    if (!end_pos) return NULL;
    
    int len = end_pos - (key_pos + 1);
    char *value = malloc(len + 1);
    if (!value) return NULL;
    
    strncpy(value, key_pos + 1, len);
    value[len] = '\0';
    
    return value;
}

double parse_json_double(const char *json, const char *key) {
    char search_key[100];
    sprintf(search_key, "\"%s\"", key);
    
    char *key_pos = strstr(json, search_key);
    if (!key_pos) return 0;
    
    key_pos = strchr(key_pos + strlen(search_key), ':');
    if (!key_pos) return 0;
    
    // Skip whitespace after colon
    while (*key_pos && (*key_pos == ':' || *key_pos == ' ' || *key_pos == '\t')) {
        key_pos++;
    }
    
    return atof(key_pos);
}

int parse_json_int(const char *json, const char *key) {
    char search_key[100];
    sprintf(search_key, "\"%s\"", key);
    
    char *key_pos = strstr(json, search_key);
    if (!key_pos) return 0;
    
    key_pos = strchr(key_pos + strlen(search_key), ':');
    if (!key_pos) return 0;
    
    // Skip whitespace after colon
    while (*key_pos && (*key_pos == ':' || *key_pos == ' ' || *key_pos == '\t')) {
        key_pos++;
    }
    
    return atoi(key_pos);
}

int is_separator(char c) {
    return c == '.' || c == '!' || c == '?';
}

void split_text_into_sentences(char *text, Sentence *sentences, int *sentence_count) {
    char *input = strdup(text);
    char *p = input;
    int i = 0;
    char sentence_buffer[MAX_SENTENCE_LEN];
    int buffer_pos = 0;
    int in_quote = 0;
    
    while (*p && i < MAX_SENTENCES) {
        // Keep track of quotes to avoid breaking sentences inside quotations
        if (*p == '"' || *p == '\'') {
            in_quote = !in_quote;
        }
        
        sentence_buffer[buffer_pos++] = *p;
        
        // Check for sentence-ending punctuation
        if (!in_quote && is_separator(*p) && (p[1] == ' ' || p[1] == '\n' || p[1] == '\0')) {
            sentence_buffer[buffer_pos] = '\0';
            
            // Trim and create sentence if non-empty
            char *trimmed = trim(sentence_buffer);
            if (strlen(trimmed) > 0) {
                sentences[i].text = strdup(trimmed);
                sentences[i].index = i;
                sentences[i].score = 1.0;  // Initial score
                i++;
            }
            
            buffer_pos = 0;
        }
        
        p++;
    }
    
    // Handle last sentence if it doesn't end with a separator
    if (buffer_pos > 0) {
        sentence_buffer[buffer_pos] = '\0';
        char *trimmed = trim(sentence_buffer);
        if (strlen(trimmed) > 0) {
            sentences[i].text = strdup(trimmed);
            sentences[i].index = i;
            sentences[i].score = 1.0;  // Initial score
            i++;
        }
    }
    
    *sentence_count = i;
    free(input);
}

void extract_words(Sentence *sentence) {
    char *text = strdup(sentence->text);
    char *p = text;
    int i = 0;
    char word[MAX_WORD_LEN];
    int word_pos = 0;
    
    sentence->words = malloc(MAX_WORDS * sizeof(char*));
    
    while (*p && i < MAX_WORDS) {
        if (isalnum(*p)) {
            word[word_pos++] = tolower(*p);
        } else if (word_pos > 0) {
            word[word_pos] = '\0';
            sentence->words[i] = strdup(word);
            i++;
            word_pos = 0;
        }
        p++;
    }
    
    // Handle last word
    if (word_pos > 0) {
        word[word_pos] = '\0';
        sentence->words[i] = strdup(word);
        i++;
    }
    
    sentence->word_count = i;
    free(text);
}

double calculate_similarity(Sentence *s1, Sentence *s2) {
    if (s1->word_count == 0 || s2->word_count == 0) return 0.0;
    
    int common_words = 0;
    
    // Count common words (simple approach for demonstration)
    for (int i = 0; i < s1->word_count; i++) {
        for (int j = 0; j < s2->word_count; j++) {
            if (strcmp(s1->words[i], s2->words[j]) == 0) {
                common_words++;
                break;
            }
        }
    }
    
    // Use Jaccard similarity
    return (double)common_words / (s1->word_count + s2->word_count - common_words);
}

void text_rank(Sentence *sentences, int sentence_count, double damping, int iterations) {
    double **similarity = malloc(sentence_count * sizeof(double*));
    for (int i = 0; i < sentence_count; i++) {
        similarity[i] = malloc(sentence_count * sizeof(double));
    }
    
    // Calculate similarity matrix
    for (int i = 0; i < sentence_count; i++) {
        for (int j = 0; j < sentence_count; j++) {
            if (i == j) {
                similarity[i][j] = 0.0;
            } else {
                similarity[i][j] = calculate_similarity(&sentences[i], &sentences[j]);
            }
        }
    }
    
    // Calculate row sums for normalization
    double *row_sums = malloc(sentence_count * sizeof(double));
    for (int i = 0; i < sentence_count; i++) {
        row_sums[i] = 0.0;
        for (int j = 0; j < sentence_count; j++) {
            row_sums[i] += similarity[i][j];
        }
    }
    
    // Normalize similarity matrix
    for (int i = 0; i < sentence_count; i++) {
        for (int j = 0; j < sentence_count; j++) {
            if (row_sums[i] > 0) {
                similarity[i][j] /= row_sums[i];
            }
        }
    }
    
    // TextRank iterations
    double *scores = malloc(sentence_count * sizeof(double));
    double *new_scores = malloc(sentence_count * sizeof(double));
    
    // Initialize scores
    for (int i = 0; i < sentence_count; i++) {
        scores[i] = 1.0 / sentence_count;
    }
    
    // TextRank algorithm iterations
    for (int iter = 0; iter < iterations; iter++) {
        for (int i = 0; i < sentence_count; i++) {
            new_scores[i] = (1.0 - damping) / sentence_count;
            
            for (int j = 0; j < sentence_count; j++) {
                if (i != j && row_sums[j] > 0) {
                    new_scores[i] += damping * similarity[j][i] * scores[j];
                }
            }
        }
        
        // Update scores
        for (int i = 0; i < sentence_count; i++) {
            scores[i] = new_scores[i];
        }
    }
    
    // Set final scores
    for (int i = 0; i < sentence_count; i++) {
        sentences[i].score = scores[i];
    }
    
    // Clean up
    free(scores);
    free(new_scores);
    free(row_sums);
    for (int i = 0; i < sentence_count; i++) {
        free(similarity[i]);
    }
    free(similarity);
}

void select_top_sentences(Sentence *sentences, int sentence_count, Sentence *selected, 
                         int *selected_count, double compression_ratio) {
    // Sort sentences by score (descending)
    Sentence *temp = malloc(sentence_count * sizeof(Sentence));
    memcpy(temp, sentences, sentence_count * sizeof(Sentence));
    
    // Simple bubble sort for demonstration
    for (int i = 0; i < sentence_count - 1; i++) {
        for (int j = 0; j < sentence_count - i - 1; j++) {
            if (temp[j].score < temp[j + 1].score) {
                Sentence swap = temp[j];
                temp[j] = temp[j + 1];
                temp[j + 1] = swap;
            }
        }
    }
    
    // Select top sentences based on compression ratio
    int to_select = (int)(sentence_count * compression_ratio);
    if (to_select < 1) to_select = 1;
    
    // Copy selected sentences
    for (int i = 0; i < to_select && i < sentence_count; i++) {
        selected[i] = temp[i];
    }
    *selected_count = to_select;
    
    // Sort selected sentences by original index
    qsort(selected, to_select, sizeof(Sentence), compare_sentences_by_index);
    
    free(temp);
}

int compare_sentences_by_index(const void *a, const void *b) {
    return ((Sentence*)a)->index - ((Sentence*)b)->index;
}

void free_sentences(Sentence *sentences, int sentence_count) {
    for (int i = 0; i < sentence_count; i++) {
        if (sentences[i].text) free(sentences[i].text);
        
        if (sentences[i].words) {
            for (int j = 0; j < sentences[i].word_count; j++) {
                if (sentences[i].words[j]) free(sentences[i].words[j]);
            }
            free(sentences[i].words);
        }
    }
}

void output_json(Sentence *selected, int selected_count) {
    printf("{\"compressed_text\": \"");
    
    for (int i = 0; i < selected_count; i++) {
        // Print each sentence, escaping quotes
        char *p = selected[i].text;
        while (*p) {
            if (*p == '"') printf("\\\"");
            else if (*p == '\\') printf("\\\\");
            else putchar(*p);
            p++;
        }
        
        // Add space between sentences
        if (i < selected_count - 1) printf(" ");
    }
    
    // Calculate the actual compression ratio based on selected_count and total sentences
    double compression_ratio = 1.0;
    if (selected_count > 0) {
        // Find max index to determine the total number of sentences
        int max_index = 0;
        for (int i = 0; i < selected_count; i++) {
            if (selected[i].index > max_index) {
                max_index = selected[i].index;
            }
        }
        int total_sentences = max_index + 1; // Convert from 0-indexed to count
        
        if (total_sentences > selected_count) {
            compression_ratio = (double)selected_count / total_sentences;
        }
    }
    
    printf("\", \"compression_ratio\": %.2f}\n", compression_ratio);
}

char *trim(char *str) {
    char *end;
    
    // Trim leading spaces
    while(isspace((unsigned char)*str)) str++;
    
    if(*str == 0) return str; // All spaces?
    
    // Trim trailing spaces
    end = str + strlen(str) - 1;
    while(end > str && isspace((unsigned char)*end)) end--;
    
    end[1] = '\0';
    
    return str;
}

package main

import (
	"strings"
	"testing"
)

func TestParseCommandsExtractsFlatList(t *testing.T) {
	commands := parseCommands(strings.NewReader("- echo one\n- echo two\n"))

	want := []string{"echo one", "echo two"}
	if len(commands) != len(want) {
		t.Fatalf("got %v, want %v", commands, want)
	}
	for i := range want {
		if commands[i] != want[i] {
			t.Fatalf("got %v, want %v", commands, want)
		}
	}
}

func TestParseCommandsIgnoresNonListLines(t *testing.T) {
	input := "# a comment\n\n- echo one\nnot a list item\n- echo two\n"
	commands := parseCommands(strings.NewReader(input))

	want := []string{"echo one", "echo two"}
	if len(commands) != len(want) {
		t.Fatalf("got %v, want %v", commands, want)
	}
	for i := range want {
		if commands[i] != want[i] {
			t.Fatalf("got %v, want %v", commands, want)
		}
	}
}

func TestParseCommandsReturnsEmptyForEmptyInput(t *testing.T) {
	commands := parseCommands(strings.NewReader(""))

	if len(commands) != 0 {
		t.Fatalf("expected no commands, got %v", commands)
	}
}

func TestParseCommandsPreservesOrder(t *testing.T) {
	commands := parseCommands(strings.NewReader("- first\n- second\n- third\n"))

	want := []string{"first", "second", "third"}
	if len(commands) != len(want) {
		t.Fatalf("got %v, want %v", commands, want)
	}
	for i := range want {
		if commands[i] != want[i] {
			t.Fatalf("position %d: got %q, want %q", i, commands[i], want[i])
		}
	}
}
